#include "vad_detector.h"
#include <iostream>
#include <cmath>

VADDetector::VADDetector(uint32_t sample_rate)
    : sample_rate_(sample_rate)
    , barge_in_enabled_(false)
    , speech_active_(false)
{
}

VADDetector::~VADDetector() {
}

bool VADDetector::initialize(const char* model_path) {
    // TODO: Initialize Silero VAD here
    // For now, using simplified VAD
    std::cout << "VAD detector initialized" << std::endl;
    std::cout << "NOTE: Using simplified VAD. Integrate Silero VAD for production use." << std::endl;
    return true;
}

void VADDetector::process(const int16_t* samples, size_t count) {
    // TODO: Process with Silero VAD
    // For now, using simple energy-based VAD
    simple_vad(samples, count);
}

void VADDetector::set_params(const Params& params) {
    params_ = params;
    std::cout << "VAD params updated: threshold=" << params.threshold
              << ", min_speech=" << params.min_speech_duration_ms << "ms"
              << ", min_silence=" << params.min_silence_duration_ms << "ms" << std::endl;
}

void VADDetector::set_barge_in_enabled(bool enabled) {
    barge_in_enabled_.store(enabled);
    std::cout << "Barge-in detection " << (enabled ? "enabled" : "disabled") << std::endl;
}

void VADDetector::set_speech_callback(SpeechCallback callback) {
    speech_callback_ = callback;
}

void VADDetector::set_barge_in_callback(BargeInCallback callback) {
    barge_in_callback_ = callback;
}

float VADDetector::calculate_rms(const int16_t* samples, size_t count) {
    double sum = 0.0;
    for (size_t i = 0; i < count; ++i) {
        double sample = samples[i] / 32768.0;
        sum += sample * sample;
    }
    return std::sqrt(sum / count);
}

float VADDetector::calculate_zero_crossing_rate(const int16_t* samples, size_t count) {
    if (count < 2) return 0.0f;

    size_t crossings = 0;
    for (size_t i = 1; i < count; ++i) {
        if ((samples[i] >= 0 && samples[i-1] < 0) || (samples[i] < 0 && samples[i-1] >= 0)) {
            crossings++;
        }
    }
    return static_cast<float>(crossings) / count;
}

void VADDetector::simple_vad(const int16_t* samples, size_t count) {
    // Simple energy and zero-crossing based VAD
    float rms = calculate_rms(samples, count);
    float zcr = calculate_zero_crossing_rate(samples, count);

    // Combine energy and ZCR for speech detection
    // Speech typically has moderate energy and moderate ZCR
    bool is_speech = (rms > params_.energy_threshold) && (zcr > 0.05f && zcr < 0.5f);
    float confidence = is_speech ? std::min(rms / params_.energy_threshold, 1.0f) : 0.0f;

    auto now = std::chrono::steady_clock::now();

    if (is_speech) {
        if (!speech_active_.load()) {
            // Speech started
            speech_active_.store(true);
            speech_start_time_ = now;

            if (speech_callback_) {
                speech_callback_(true, confidence);
            }
        }
        last_speech_time_ = now;

        // Check for barge-in
        if (barge_in_enabled_.load() && barge_in_callback_) {
            auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
                now - speech_start_time_
            ).count();

            if (duration >= params_.min_speech_duration_ms) {
                barge_in_callback_(confidence, duration);
                barge_in_enabled_.store(false); // Fire once
            }
        }
    } else if (speech_active_.load()) {
        // Check if silence duration is sufficient to end speech
        auto silence_duration = std::chrono::duration_cast<std::chrono::milliseconds>(
            now - last_speech_time_
        ).count();

        if (silence_duration >= params_.min_silence_duration_ms) {
            // Speech ended
            speech_active_.store(false);

            if (speech_callback_) {
                speech_callback_(false, 0.0f);
            }
        }
    }
}
