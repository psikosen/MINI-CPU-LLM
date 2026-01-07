#ifndef IPC_PROTOCOL_H
#define IPC_PROTOCOL_H

#include <stdint.h>

// Protocol version
#define IPC_PROTOCOL_VERSION 1

// Maximum message size (64KB)
#define IPC_MAX_MESSAGE_SIZE 65536

// Socket path
#define IPC_SOCKET_PATH "/tmp/voice_assistant.sock"

// Message types from voice_core to orchestrator
typedef enum {
    MSG_WAKE_DETECTED = 1,
    MSG_UTTERANCE_READY = 2,
    MSG_BARGE_IN_DETECTED = 3,
    MSG_PLAYBACK_FINISHED = 4,
    MSG_CORE_HEALTH = 5,
    MSG_VAD_SPEECH_START = 6,
    MSG_VAD_SPEECH_END = 7,
    MSG_ERROR = 8
} MessageType;

// Command types from orchestrator to voice_core
typedef enum {
    CMD_PLAY_TTS = 101,
    CMD_STOP_TTS = 102,
    CMD_START_RECORD = 103,
    CMD_STOP_RECORD = 104,
    CMD_SET_VAD_PARAMS = 105,
    CMD_ENABLE_WAKEWORD = 106,
    CMD_DISABLE_WAKEWORD = 107,
    CMD_SHUTDOWN = 108,
    CMD_GET_STATUS = 109
} CommandType;

// Message header (fixed size)
typedef struct __attribute__((packed)) {
    uint8_t version;           // Protocol version
    uint8_t message_type;      // MessageType or CommandType
    uint16_t payload_length;   // Length of payload in bytes
    uint32_t sequence_number;  // Message sequence number
    uint64_t timestamp_us;     // Timestamp in microseconds
} MessageHeader;

// Wake word detected payload
typedef struct __attribute__((packed)) {
    float confidence;
    char keyword[32];
} WakeDetectedPayload;

// Utterance ready payload
typedef struct __attribute__((packed)) {
    uint32_t audio_length;     // Length of audio data in samples
    uint32_t sample_rate;      // Sample rate in Hz
    char audio_path[256];      // Path to audio file
} UtteranceReadyPayload;

// Barge-in detected payload
typedef struct __attribute__((packed)) {
    float vad_confidence;
    uint32_t speech_duration_ms;
} BargeInPayload;

// VAD parameters payload
typedef struct __attribute__((packed)) {
    float threshold;           // VAD confidence threshold (0.0-1.0)
    uint32_t min_speech_duration_ms;  // Minimum speech duration
    uint32_t min_silence_duration_ms; // Minimum silence duration
    float energy_threshold;    // RMS energy threshold
} VADParamsPayload;

// TTS playback command payload
typedef struct __attribute__((packed)) {
    uint32_t sample_rate;
    uint32_t num_channels;
    char audio_path[256];      // Path to audio file or stream
    uint8_t enable_interruption; // Allow barge-in during playback
} PlayTTSPayload;

// Health status payload
typedef struct __attribute__((packed)) {
    uint8_t is_healthy;
    float cpu_usage;
    float memory_usage_mb;
    uint64_t uptime_seconds;
} HealthPayload;

// Error payload
typedef struct __attribute__((packed)) {
    uint16_t error_code;
    char error_message[256];
} ErrorPayload;

// Generic response payload
typedef struct __attribute__((packed)) {
    uint8_t success;
    char message[256];
} ResponsePayload;

// Helper macros for message sizes
#define IPC_HEADER_SIZE sizeof(MessageHeader)
#define IPC_MESSAGE_SIZE(payload_type) (IPC_HEADER_SIZE + sizeof(payload_type))

// Status codes
typedef enum {
    IPC_SUCCESS = 0,
    IPC_ERROR_INVALID_MESSAGE = 1,
    IPC_ERROR_UNSUPPORTED_VERSION = 2,
    IPC_ERROR_PAYLOAD_TOO_LARGE = 3,
    IPC_ERROR_SOCKET_ERROR = 4,
    IPC_ERROR_TIMEOUT = 5,
    IPC_ERROR_INTERNAL = 6
} IPCStatusCode;

#endif // IPC_PROTOCOL_H
