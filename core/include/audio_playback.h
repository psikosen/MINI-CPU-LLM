#ifndef AUDIO_PLAYBACK_H
#define AUDIO_PLAYBACK_H

#include <alsa/asoundlib.h>
#include <atomic>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <vector>
#include <cstdint>
#include <functional>

class AudioPlayback {
public:
    using PlaybackFinishedCallback = std::function<void()>;

    AudioPlayback(const char* device = "default", uint32_t sample_rate = 16000, uint32_t channels = 1);
    ~AudioPlayback();

    // Start/stop playback system
    bool start();
    void stop();

    // Queue audio for playback
    bool play(const int16_t* samples, size_t count);
    bool play_file(const char* filename);

    // Stop current playback immediately
    void stop_playback();

    // Check if currently playing
    bool is_playing() const { return playing_.load(); }

    // Set callback for when playback finishes
    void set_finished_callback(PlaybackFinishedCallback callback);

private:
    void playback_thread();
    bool init_alsa();
    void cleanup_alsa();

    const char* device_;
    uint32_t sample_rate_;
    uint32_t channels_;

    snd_pcm_t* pcm_handle_;
    std::atomic<bool> running_;
    std::atomic<bool> playing_;
    std::atomic<bool> stop_requested_;
    std::thread playback_thread_;

    std::queue<std::vector<int16_t>> playback_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;

    PlaybackFinishedCallback finished_callback_;
};

#endif // AUDIO_PLAYBACK_H
