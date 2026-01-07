#include "audio_capture.h"
#include <iostream>
#include <cstring>

AudioCapture::AudioCapture(const char* device, uint32_t sample_rate, uint32_t channels)
    : device_(device)
    , sample_rate_(sample_rate)
    , channels_(channels)
    , pcm_handle_(nullptr)
    , capturing_(false)
{
}

AudioCapture::~AudioCapture() {
    stop();
}

bool AudioCapture::start() {
    if (capturing_.load()) {
        return false;
    }

    if (!init_alsa()) {
        return false;
    }

    capturing_.store(true);
    capture_thread_ = std::thread(&AudioCapture::capture_thread, this);

    std::cout << "Audio capture started: " << sample_rate_ << "Hz, " << channels_ << " channel(s)" << std::endl;
    return true;
}

void AudioCapture::stop() {
    if (!capturing_.load()) {
        return;
    }

    capturing_.store(false);

    if (capture_thread_.joinable()) {
        capture_thread_.join();
    }

    cleanup_alsa();
    std::cout << "Audio capture stopped" << std::endl;
}

void AudioCapture::set_callback(AudioCallback callback) {
    callback_ = callback;
}

bool AudioCapture::init_alsa() {
    int err;

    // Open PCM device
    err = snd_pcm_open(&pcm_handle_, device_, SND_PCM_STREAM_CAPTURE, 0);
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

void AudioCapture::cleanup_alsa() {
    if (pcm_handle_) {
        snd_pcm_drain(pcm_handle_);
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
    }
}

void AudioCapture::capture_thread() {
    int16_t buffer[BUFFER_SIZE * channels_];

    while (capturing_.load()) {
        int frames_read = snd_pcm_readi(pcm_handle_, buffer, BUFFER_SIZE);

        if (frames_read < 0) {
            // Handle errors
            if (frames_read == -EPIPE) {
                // Overrun
                std::cerr << "Audio overrun occurred" << std::endl;
                snd_pcm_prepare(pcm_handle_);
            } else {
                std::cerr << "Read error: " << snd_strerror(frames_read) << std::endl;
                break;
            }
        } else if (frames_read > 0) {
            // Invoke callback
            if (callback_) {
                callback_(buffer, frames_read * channels_);
            }
        }
    }
}
