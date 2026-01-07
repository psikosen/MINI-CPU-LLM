#include "wake_word.h"
#include <iostream>
#include <cmath>
#include <cstring>

WakeWordDetector::WakeWordDetector(uint32_t sample_rate)
    : sample_rate_(sample_rate)
    , enabled_(false)
    , sensitivity_(0.5f)
    , keyword_("computer")
{
}

WakeWordDetector::~WakeWordDetector() {
}

bool WakeWordDetector::initialize(const char* model_path, const char* keyword) {
    if (keyword) {
        keyword_ = keyword;
    }

    // TODO: Initialize Porcupine SDK here
    // For now, using simplified detection
    std::cout << "Wake word detector initialized for keyword: " << keyword_ << std::endl;
    std::cout << "NOTE: Using simplified detection. Integrate Porcupine for production use." << std::endl;

    return true;
}

void WakeWordDetector::process(const int16_t* samples, size_t count) {
    if (!enabled_.load() || !callback_) {
        return;
    }

    // TODO: Process with Porcupine SDK
    // For now, using simple energy-based detection as placeholder
    simple_detection(samples, count);
}

void WakeWordDetector::set_enabled(bool enabled) {
    enabled_.store(enabled);
    std::cout << "Wake word detection " << (enabled ? "enabled" : "disabled") << std::endl;
}

void WakeWordDetector::set_callback(WakeWordCallback callback) {
    callback_ = callback;
}

float WakeWordDetector::calculate_rms(const int16_t* samples, size_t count) {
    double sum = 0.0;
    for (size_t i = 0; i < count; ++i) {
        double sample = samples[i] / 32768.0;
        sum += sample * sample;
    }
    return std::sqrt(sum / count);
}

void WakeWordDetector::simple_detection(const int16_t* samples, size_t count) {
    // Simple energy-based detection as placeholder
    // This is NOT a real wake word detector - just for testing
    float rms = calculate_rms(samples, count);

    // Trigger on significant energy spike
    float threshold = 0.1f * sensitivity_;
    if (rms > threshold) {
        static auto last_trigger = std::chrono::steady_clock::now();
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - last_trigger).count();

        // Debounce: only trigger once per 3 seconds
        if (elapsed >= 3) {
            std::cout << "Wake word detected (simple detection, RMS: " << rms << ")" << std::endl;
            callback_(keyword_.c_str(), rms);
            last_trigger = now;
        }
    }
}

void WakeWordDetector::set_sensitivity(float sensitivity) {
    sensitivity_ = std::max(0.0f, std::min(1.0f, sensitivity));
}
