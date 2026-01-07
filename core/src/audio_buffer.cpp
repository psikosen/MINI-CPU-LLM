#include "audio_buffer.h"
#include <algorithm>
#include <cstring>

AudioBuffer::AudioBuffer(size_t capacity)
    : capacity_(capacity)
    , read_pos_(0)
    , write_pos_(0)
    , size_(0)
{
    buffer_.resize(capacity);
}

void AudioBuffer::write(const int16_t* samples, size_t count) {
    std::lock_guard<std::mutex> lock(mutex_);

    for (size_t i = 0; i < count; ++i) {
        buffer_[write_pos_] = samples[i];
        write_pos_ = (write_pos_ + 1) % capacity_;

        if (size_ < capacity_) {
            size_++;
        } else {
            // Buffer full, overwrite oldest data
            read_pos_ = (read_pos_ + 1) % capacity_;
        }
    }
}

size_t AudioBuffer::read(int16_t* samples, size_t count) {
    std::lock_guard<std::mutex> lock(mutex_);

    size_t to_read = std::min(count, size_);

    for (size_t i = 0; i < to_read; ++i) {
        samples[i] = buffer_[read_pos_];
        read_pos_ = (read_pos_ + 1) % capacity_;
    }

    size_ -= to_read;
    return to_read;
}

size_t AudioBuffer::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return size_;
}

void AudioBuffer::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    read_pos_ = 0;
    write_pos_ = 0;
    size_ = 0;
}

bool AudioBuffer::empty() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return size_ == 0;
}

std::vector<int16_t> AudioBuffer::get_all() {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<int16_t> result;
    result.reserve(size_);

    size_t pos = read_pos_;
    for (size_t i = 0; i < size_; ++i) {
        result.push_back(buffer_[pos]);
        pos = (pos + 1) % capacity_;
    }

    read_pos_ = 0;
    write_pos_ = 0;
    size_ = 0;

    return result;
}
