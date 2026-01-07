#ifndef WAKE_WORD_H
#define WAKE_WORD_H

#include <atomic>
#include <functional>
#include <cstdint>
#include <string>

// Simplified wake word detector interface
// In production, this would integrate with Porcupine SDK
class WakeWordDetector {
public:
    using WakeWordCallback = std::function<void(const char* keyword, float confidence)>;

    WakeWordDetector(uint32_t sample_rate = 16000);
    ~WakeWordDetector();

    // Initialize detector with keyword model
    bool initialize(const char* model_path = nullptr, const char* keyword = "computer");

    // Process audio samples
    void process(const int16_t* samples, size_t count);

    // Enable/disable detection
    void set_enabled(bool enabled);
    bool is_enabled() const { return enabled_.load(); }

    // Set callback for wake word detection
    void set_callback(WakeWordCallback callback);

    // Get sensitivity (0.0 - 1.0)
    float get_sensitivity() const { return sensitivity_; }
    void set_sensitivity(float sensitivity);

private:
    uint32_t sample_rate_;
    std::atomic<bool> enabled_;
    float sensitivity_;
    WakeWordCallback callback_;
    std::string keyword_;

    // Simple energy-based detection for demo
    // TODO: Replace with Porcupine integration
    void simple_detection(const int16_t* samples, size_t count);
    float calculate_rms(const int16_t* samples, size_t count);
};

#endif // WAKE_WORD_H
