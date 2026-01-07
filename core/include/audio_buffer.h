#ifndef AUDIO_BUFFER_H
#define AUDIO_BUFFER_H

#include <vector>
#include <mutex>
#include <cstdint>

class AudioBuffer {
public:
    AudioBuffer(size_t capacity);

    // Write samples to buffer
    void write(const int16_t* samples, size_t count);

    // Read samples from buffer
    size_t read(int16_t* samples, size_t count);

    // Get current size
    size_t size() const;

    // Clear buffer
    void clear();

    // Check if empty
    bool empty() const;

    // Get all data and clear
    std::vector<int16_t> get_all();

private:
    std::vector<int16_t> buffer_;
    size_t capacity_;
    size_t read_pos_;
    size_t write_pos_;
    size_t size_;
    mutable std::mutex mutex_;
};

#endif // AUDIO_BUFFER_H
