#ifndef AUDIO_CAPTURE_H
#define AUDIO_CAPTURE_H

#include <alsa/asoundlib.h>
#include <atomic>
#include <thread>
#include <functional>
#include <cstdint>

class AudioCapture {
public:
    using AudioCallback = std::function<void(const int16_t* samples, size_t count)>;

    AudioCapture(const char* device = "default", uint32_t sample_rate = 16000, uint32_t channels = 1);
    ~AudioCapture();

    // Start/stop capture
    bool start();
    void stop();

    // Set callback for audio data
    void set_callback(AudioCallback callback);

    // Check if capturing
    bool is_capturing() const { return capturing_.load(); }

    // Get audio parameters
    uint32_t get_sample_rate() const { return sample_rate_; }
    uint32_t get_channels() const { return channels_; }

private:
    void capture_thread();
    bool init_alsa();
    void cleanup_alsa();

    const char* device_;
    uint32_t sample_rate_;
    uint32_t channels_;

    snd_pcm_t* pcm_handle_;
    std::atomic<bool> capturing_;
    std::thread capture_thread_;
    AudioCallback callback_;

    static constexpr size_t BUFFER_SIZE = 1024;
};

#endif // AUDIO_CAPTURE_H
