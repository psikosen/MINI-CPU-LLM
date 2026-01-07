#include "ipc_server.h"
#include "audio_capture.h"
#include "audio_playback.h"
#include "vad_detector.h"
#include "wake_word.h"
#include "audio_buffer.h"
#include <iostream>
#include <csignal>
#include <atomic>
#include <fstream>
#include <cstring>

// Global state
static std::atomic<bool> g_running(true);
static IPCServer* g_ipc_server = nullptr;

// Signal handler
void signal_handler(int signal) {
    std::cout << "\nReceived signal " << signal << ", shutting down..." << std::endl;
    g_running.store(false);
}

// Voice core state machine
enum class CoreState {
    IDLE,
    LISTENING,
    RECORDING,
    PLAYING
};

class VoiceCore {
public:
    VoiceCore()
        : state_(CoreState::IDLE)
        , recording_buffer_(16000 * 10) // 10 seconds buffer
        , utterance_counter_(0)
    {
    }

    bool initialize() {
        // Initialize IPC server
        ipc_server_.set_command_callback([this](uint8_t type, const uint8_t* payload, uint16_t len) {
            handle_command(type, payload, len);
        });

        if (!ipc_server_.start()) {
            std::cerr << "Failed to start IPC server" << std::endl;
            return false;
        }

        // Initialize audio capture
        audio_capture_.set_callback([this](const int16_t* samples, size_t count) {
            handle_audio_input(samples, count);
        });

        if (!audio_capture_.start()) {
            std::cerr << "Failed to start audio capture" << std::endl;
            return false;
        }

        // Initialize audio playback
        audio_playback_.set_finished_callback([this]() {
            handle_playback_finished();
        });

        if (!audio_playback_.start()) {
            std::cerr << "Failed to start audio playback" << std::endl;
            return false;
        }

        // Initialize wake word detector
        wake_word_.initialize(nullptr, "computer");
        wake_word_.set_callback([this](const char* keyword, float confidence) {
            handle_wake_word(keyword, confidence);
        });
        wake_word_.set_enabled(true);

        // Initialize VAD detector
        vad_.initialize();
        vad_.set_speech_callback([this](bool is_speech, float confidence) {
            handle_vad_speech(is_speech, confidence);
        });
        vad_.set_barge_in_callback([this](float confidence, uint32_t duration_ms) {
            handle_barge_in(confidence, duration_ms);
        });

        std::cout << "Voice core initialized successfully" << std::endl;
        return true;
    }

    void run() {
        std::cout << "Voice core running. Waiting for wake word..." << std::endl;

        while (g_running.load()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));

            // Send periodic health updates
            static auto last_health = std::chrono::steady_clock::now();
            auto now = std::chrono::steady_clock::now();
            if (std::chrono::duration_cast<std::chrono::seconds>(now - last_health).count() >= 30) {
                send_health_update();
                last_health = now;
            }
        }
    }

    void shutdown() {
        std::cout << "Shutting down voice core..." << std::endl;
        wake_word_.set_enabled(false);
        audio_capture_.stop();
        audio_playback_.stop();
        ipc_server_.stop();
    }

private:
    void handle_audio_input(const int16_t* samples, size_t count) {
        // Always process through wake word and VAD
        wake_word_.process(samples, count);
        vad_.process(samples, count);

        // If recording, buffer the audio
        if (state_ == CoreState::RECORDING) {
            recording_buffer_.write(samples, count);
        }
    }

    void handle_wake_word(const char* keyword, float confidence) {
        std::cout << "Wake word detected: " << keyword << " (confidence: " << confidence << ")" << std::endl;

        // Send wake detected message
        WakeDetectedPayload payload;
        payload.confidence = confidence;
        strncpy(payload.keyword, keyword, sizeof(payload.keyword) - 1);
        ipc_server_.send_message(MSG_WAKE_DETECTED, &payload, sizeof(payload));

        // Start recording
        start_recording();
    }

    void handle_vad_speech(bool is_speech, float confidence) {
        if (!is_speech && state_ == CoreState::RECORDING) {
            // End of speech detected
            std::cout << "End of speech detected" << std::endl;
            stop_recording();
        }
    }

    void handle_barge_in(float confidence, uint32_t duration_ms) {
        std::cout << "Barge-in detected! confidence: " << confidence
                  << ", duration: " << duration_ms << "ms" << std::endl;

        // Stop playback immediately
        audio_playback_.stop_playback();

        // Send barge-in message
        BargeInPayload payload;
        payload.vad_confidence = confidence;
        payload.speech_duration_ms = duration_ms;
        ipc_server_.send_message(MSG_BARGE_IN_DETECTED, &payload, sizeof(payload));

        // Start recording new utterance
        start_recording();
    }

    void handle_playback_finished() {
        std::cout << "Playback finished" << std::endl;
        state_ = CoreState::IDLE;

        // Disable barge-in
        vad_.set_barge_in_enabled(false);

        // Send playback finished message
        ipc_server_.send_message(MSG_PLAYBACK_FINISHED, nullptr, 0);
    }

    void handle_command(uint8_t type, const uint8_t* payload, uint16_t len) {
        switch (type) {
            case CMD_PLAY_TTS: {
                if (len >= sizeof(PlayTTSPayload)) {
                    const PlayTTSPayload* cmd = reinterpret_cast<const PlayTTSPayload*>(payload);
                    play_tts(cmd);
                }
                break;
            }

            case CMD_STOP_TTS: {
                audio_playback_.stop_playback();
                break;
            }

            case CMD_SET_VAD_PARAMS: {
                if (len >= sizeof(VADParamsPayload)) {
                    const VADParamsPayload* cmd = reinterpret_cast<const VADParamsPayload*>(payload);
                    set_vad_params(cmd);
                }
                break;
            }

            case CMD_ENABLE_WAKEWORD: {
                wake_word_.set_enabled(true);
                break;
            }

            case CMD_DISABLE_WAKEWORD: {
                wake_word_.set_enabled(false);
                break;
            }

            case CMD_SHUTDOWN: {
                g_running.store(false);
                break;
            }

            default:
                std::cerr << "Unknown command: " << (int)type << std::endl;
                break;
        }
    }

    void start_recording() {
        std::cout << "Starting recording..." << std::endl;
        state_ = CoreState::RECORDING;
        recording_buffer_.clear();

        // Disable wake word during recording
        wake_word_.set_enabled(false);
    }

    void stop_recording() {
        std::cout << "Stopping recording..." << std::endl;
        state_ = CoreState::IDLE;

        // Save recorded audio to file
        auto audio_data = recording_buffer_.get_all();
        if (!audio_data.empty()) {
            char filename[256];
            snprintf(filename, sizeof(filename), "/tmp/utterance_%u.raw", utterance_counter_++);
            save_audio_file(filename, audio_data.data(), audio_data.size());

            // Send utterance ready message
            UtteranceReadyPayload payload;
            payload.audio_length = audio_data.size();
            payload.sample_rate = 16000;
            strncpy(payload.audio_path, filename, sizeof(payload.audio_path) - 1);
            ipc_server_.send_message(MSG_UTTERANCE_READY, &payload, sizeof(payload));
        }

        // Re-enable wake word
        wake_word_.set_enabled(true);
    }

    void play_tts(const PlayTTSPayload* cmd) {
        std::cout << "Playing TTS: " << cmd->audio_path << std::endl;
        state_ = CoreState::PLAYING;

        // Enable barge-in if requested
        if (cmd->enable_interruption) {
            vad_.set_barge_in_enabled(true);
        }

        // Play audio file
        audio_playback_.play_file(cmd->audio_path);
    }

    void set_vad_params(const VADParamsPayload* cmd) {
        VADDetector::Params params;
        params.threshold = cmd->threshold;
        params.min_speech_duration_ms = cmd->min_speech_duration_ms;
        params.min_silence_duration_ms = cmd->min_silence_duration_ms;
        params.energy_threshold = cmd->energy_threshold;
        vad_.set_params(params);
    }

    void save_audio_file(const char* filename, const int16_t* data, size_t count) {
        std::ofstream file(filename, std::ios::binary);
        if (file) {
            file.write(reinterpret_cast<const char*>(data), count * sizeof(int16_t));
            std::cout << "Saved audio to: " << filename << " (" << count << " samples)" << std::endl;
        } else {
            std::cerr << "Failed to save audio file: " << filename << std::endl;
        }
    }

    void send_health_update() {
        HealthPayload payload;
        payload.is_healthy = 1;
        payload.cpu_usage = 0.0f; // TODO: Implement actual CPU monitoring
        payload.memory_usage_mb = 0.0f; // TODO: Implement actual memory monitoring
        payload.uptime_seconds = 0; // TODO: Track uptime
        ipc_server_.send_message(MSG_CORE_HEALTH, &payload, sizeof(payload));
    }

    CoreState state_;
    IPCServer ipc_server_;
    AudioCapture audio_capture_;
    AudioPlayback audio_playback_;
    VADDetector vad_;
    WakeWordDetector wake_word_;
    AudioBuffer recording_buffer_;
    uint32_t utterance_counter_;
};

int main(int argc, char* argv[]) {
    std::cout << "Voice Core v1.0.0" << std::endl;
    std::cout << "==================" << std::endl;

    // Setup signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    // Create and initialize voice core
    VoiceCore core;
    if (!core.initialize()) {
        std::cerr << "Failed to initialize voice core" << std::endl;
        return 1;
    }

    // Run main loop
    core.run();

    // Shutdown
    core.shutdown();

    std::cout << "Voice core stopped" << std::endl;
    return 0;
}
