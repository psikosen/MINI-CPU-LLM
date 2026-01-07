#include "audio_playback.h"
#include <iostream>
#include <fstream>
#include <cstring>

AudioPlayback::AudioPlayback(const char* device, uint32_t sample_rate, uint32_t channels)
    : device_(device)
    , sample_rate_(sample_rate)
    , channels_(channels)
    , pcm_handle_(nullptr)
    , running_(false)
    , playing_(false)
    , stop_requested_(false)
{
}

AudioPlayback::~AudioPlayback() {
    stop();
}

bool AudioPlayback::start() {
    if (running_.load()) {
        return false;
    }

    if (!init_alsa()) {
        return false;
    }

    running_.store(true);
    playback_thread_ = std::thread(&AudioPlayback::playback_thread, this);

    std::cout << "Audio playback started: " << sample_rate_ << "Hz, " << channels_ << " channel(s)" << std::endl;
    return true;
}

void AudioPlayback::stop() {
    if (!running_.load()) {
        return;
    }

    running_.store(false);
    queue_cv_.notify_all();

    if (playback_thread_.joinable()) {
        playback_thread_.join();
    }

    cleanup_alsa();
    std::cout << "Audio playback stopped" << std::endl;
}

bool AudioPlayback::play(const int16_t* samples, size_t count) {
    if (!running_.load()) {
        return false;
    }

    std::lock_guard<std::mutex> lock(queue_mutex_);
    playback_queue_.emplace(samples, samples + count);
    queue_cv_.notify_one();
    return true;
}

bool AudioPlayback::play_file(const char* filename) {
    // Simple WAV file reader (assumes 16-bit PCM, same format as our settings)
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        std::cerr << "Cannot open file: " << filename << std::endl;
        return false;
    }

    // Skip WAV header (44 bytes for standard PCM WAV)
    file.seekg(44, std::ios::beg);

    // Read audio data
    std::vector<int16_t> audio_data;
    int16_t sample;
    while (file.read(reinterpret_cast<char*>(&sample), sizeof(sample))) {
        audio_data.push_back(sample);
    }

    if (audio_data.empty()) {
        std::cerr << "No audio data in file: " << filename << std::endl;
        return false;
    }

    return play(audio_data.data(), audio_data.size());
}

void AudioPlayback::stop_playback() {
    stop_requested_.store(true);

    // Clear queue
    std::lock_guard<std::mutex> lock(queue_mutex_);
    while (!playback_queue_.empty()) {
        playback_queue_.pop();
    }
}

void AudioPlayback::set_finished_callback(PlaybackFinishedCallback callback) {
    finished_callback_ = callback;
}

bool AudioPlayback::init_alsa() {
    int err;

    // Open PCM device
    err = snd_pcm_open(&pcm_handle_, device_, SND_PCM_STREAM_PLAYBACK, 0);
    if (err < 0) {
        std::cerr << "Cannot open audio device " << device_ << ": " << snd_strerror(err) << std::endl;
        return false;
    }

    // Allocate hardware parameters
    snd_pcm_hw_params_t* hw_params;
    snd_pcm_hw_params_alloca(&hw_params);

    // Initialize hardware parameters
    err = snd_pcm_hw_params_any(pcm_handle_, hw_params);
    if (err < 0) {
        std::cerr << "Cannot initialize hardware parameters: " << snd_strerror(err) << std::endl;
        cleanup_alsa();
        return false;
    }

    // Set access type
    err = snd_pcm_hw_params_set_access(pcm_handle_, hw_params, SND_PCM_ACCESS_RW_INTERLEAVED);
    if (err < 0) {
        std::cerr << "Cannot set access type: " << snd_strerror(err) << std::endl;
        cleanup_alsa();
        return false;
    }

    // Set sample format (16-bit signed little-endian)
    err = snd_pcm_hw_params_set_format(pcm_handle_, hw_params, SND_PCM_FORMAT_S16_LE);
    if (err < 0) {
        std::cerr << "Cannot set sample format: " << snd_strerror(err) << std::endl;
        cleanup_alsa();
        return false;
    }

    // Set sample rate
    err = snd_pcm_hw_params_set_rate_near(pcm_handle_, hw_params, &sample_rate_, 0);
    if (err < 0) {
        std::cerr << "Cannot set sample rate: " << snd_strerror(err) << std::endl;
        cleanup_alsa();
        return false;
    }

    // Set number of channels
    err = snd_pcm_hw_params_set_channels(pcm_handle_, hw_params, channels_);
    if (err < 0) {
        std::cerr << "Cannot set channel count: " << snd_strerror(err) << std::endl;
        cleanup_alsa();
        return false;
    }

    // Apply hardware parameters
    err = snd_pcm_hw_params(pcm_handle_, hw_params);
    if (err < 0) {
        std::cerr << "Cannot set hardware parameters: " << snd_strerror(err) << std::endl;
        cleanup_alsa();
        return false;
    }

    // Prepare PCM device
    err = snd_pcm_prepare(pcm_handle_);
    if (err < 0) {
        std::cerr << "Cannot prepare audio interface: " << snd_strerror(err) << std::endl;
        cleanup_alsa();
        return false;
    }

    return true;
}

void AudioPlayback::cleanup_alsa() {
    if (pcm_handle_) {
        snd_pcm_drain(pcm_handle_);
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
    }
}

void AudioPlayback::playback_thread() {
    const size_t chunk_size = 1024;

    while (running_.load()) {
        std::vector<int16_t> audio_data;

        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            queue_cv_.wait(lock, [this] {
                return !playback_queue_.empty() || !running_.load();
            });

            if (!running_.load()) {
                break;
            }

            if (!playback_queue_.empty()) {
                audio_data = std::move(playback_queue_.front());
                playback_queue_.pop();
            }
        }

        if (audio_data.empty()) {
            continue;
        }

        playing_.store(true);
        stop_requested_.store(false);

        size_t offset = 0;
        while (offset < audio_data.size() && !stop_requested_.load()) {
            size_t frames = std::min(chunk_size, audio_data.size() - offset);
            int frames_written = snd_pcm_writei(pcm_handle_, &audio_data[offset], frames);

            if (frames_written < 0) {
                // Handle errors
                if (frames_written == -EPIPE) {
                    // Underrun
                    std::cerr << "Audio underrun occurred" << std::endl;
                    snd_pcm_prepare(pcm_handle_);
                } else {
                    std::cerr << "Write error: " << snd_strerror(frames_written) << std::endl;
                    break;
                }
            } else {
                offset += frames_written;
            }
        }

        playing_.store(false);

        // Invoke callback
        if (finished_callback_ && !stop_requested_.load()) {
            finished_callback_();
        }
    }
}
