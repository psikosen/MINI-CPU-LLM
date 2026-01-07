#ifndef IPC_SERVER_H
#define IPC_SERVER_H

#include "ipc_protocol.h"
#include <functional>
#include <thread>
#include <atomic>
#include <queue>
#include <mutex>

class IPCServer {
public:
    using MessageCallback = std::function<void(uint8_t msg_type, const uint8_t* payload, uint16_t payload_len)>;

    IPCServer(const char* socket_path = IPC_SOCKET_PATH);
    ~IPCServer();

    // Start/stop the server
    bool start();
    void stop();

    // Send message to orchestrator
    bool send_message(uint8_t msg_type, const void* payload, uint16_t payload_len);

    // Set callback for incoming commands
    void set_command_callback(MessageCallback callback);

    // Check if server is running
    bool is_running() const { return running_.load(); }

private:
    void server_thread();
    void handle_client(int client_fd);
    bool send_to_client(int fd, const uint8_t* data, size_t len);
    bool recv_from_client(int fd, uint8_t* buffer, size_t len);

    const char* socket_path_;
    int server_fd_;
    int client_fd_;
    std::atomic<bool> running_;
    std::thread server_thread_;
    MessageCallback command_callback_;

    uint32_t sequence_number_;
    std::mutex send_mutex_;
};

#endif // IPC_SERVER_H
