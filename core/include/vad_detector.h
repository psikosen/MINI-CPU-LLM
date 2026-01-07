#ifndef VAD_DETECTOR_H
#define VAD_DETECTOR_H

#include <atomic>
#include <functional>
#include <cstdint>
#include <chrono>

// Simplified VAD detector interface
// In production, this would integrate with Silero VAD
class VADDetector {
public:
    using SpeechCallback = std::function<void(bool is_speech, float confidence)>;
    using BargeInCallback = std::function<void(float confidence, uint32_t duration_ms)>;

    struct Params {
        float threshold = 0.65f;                    // VAD confidence threshold
        uint32_t min_speech_duration_ms = 300;      // Minimum speech duration for barge-in
        uint32_t min_silence_duration_ms = 500;     // Minimum silence to end speech
        float energy_threshold = 0.02f;             // RMS energy threshold
    };

    VADDetector(uint32_t sample_rate = 16000);
    ~VADDetector();

    // Initialize detector
    bool initialize(const char* model_path = nullptr);

    // Process audio samples
    void process(const int16_t* samples, size_t count);

    // Set parameters
    void set_params(const Params& params);
    Params get_params() const { return params_; }

    // Enable/disable barge-in detection
    void set_barge_in_enabled(bool enabled);
    bool is_barge_in_enabled() const { return barge_in_enabled_.load(); }

    // Set callbacks
    void set_speech_callback(SpeechCallback callback);
    void set_barge_in_callback(BargeInCallback callback);

    // Get current state
    bool is_speech_active() const { return speech_active_.load(); }

private:
    uint32_t sample_rate_;
    Params params_;
    std::atomic<bool> barge_in_enabled_;
    std::atomic<bool> speech_active_;

    SpeechCallback speech_callback_;
    BargeInCallback barge_in_callback_;

    std::chrono::steady_clock::time_point speech_start_time_;
    std::chrono::steady_clock::time_point last_speech_time_;

    // Simple VAD for demo
    // TODO: Replace with Silero VAD integration
    void simple_vad(const int16_t* samples, size_t count);
    float calculate_rms(const int16_t* samples, size_t count);
    float calculate_zero_crossing_rate(const int16_t* samples, size_t count);
};

#endif // VAD_DETECTOR_H
