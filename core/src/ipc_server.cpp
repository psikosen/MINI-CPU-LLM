#include "ipc_server.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <cstring>
#include <iostream>
#include <chrono>

IPCServer::IPCServer(const char* socket_path)
    : socket_path_(socket_path)
    , server_fd_(-1)
    , client_fd_(-1)
    , running_(false)
    , sequence_number_(0)
{
}

IPCServer::~IPCServer() {
    stop();
}

bool IPCServer::start() {
    if (running_.load()) {
        return false;
    }

    // Remove existing socket file
    unlink(socket_path_);

    // Create socket
    server_fd_ = socket(AF_UNIX, SOCK_STREAM, 0);
    if (server_fd_ < 0) {
        std::cerr << "Failed to create socket: " << strerror(errno) << std::endl;
        return false;
    }

    // Bind socket
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socket_path_, sizeof(addr.sun_path) - 1);

    if (bind(server_fd_, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        std::cerr << "Failed to bind socket: " << strerror(errno) << std::endl;
        close(server_fd_);
        return false;
    }

    // Listen
    if (listen(server_fd_, 1) < 0) {
        std::cerr << "Failed to listen on socket: " << strerror(errno) << std::endl;
        close(server_fd_);
        return false;
    }

    running_.store(true);
    server_thread_ = std::thread(&IPCServer::server_thread, this);

    std::cout << "IPC Server started on " << socket_path_ << std::endl;
    return true;
}

void IPCServer::stop() {
    if (!running_.load()) {
        return;
    }

    running_.store(false);

    if (client_fd_ >= 0) {
        close(client_fd_);
        client_fd_ = -1;
    }

    if (server_fd_ >= 0) {
        close(server_fd_);
        server_fd_ = -1;
    }

    if (server_thread_.joinable()) {
        server_thread_.join();
    }

    unlink(socket_path_);
    std::cout << "IPC Server stopped" << std::endl;
}

void IPCServer::server_thread() {
    while (running_.load()) {
        // Accept client connection
        struct sockaddr_un client_addr;
        socklen_t client_len = sizeof(client_addr);

        int client_fd = accept(server_fd_, (struct sockaddr*)&client_addr, &client_len);
        if (client_fd < 0) {
            if (running_.load()) {
                std::cerr << "Accept failed: " << strerror(errno) << std::endl;
            }
            continue;
        }

        std::cout << "Client connected" << std::endl;
        client_fd_ = client_fd;
        handle_client(client_fd);

        close(client_fd);
        client_fd_ = -1;
        std::cout << "Client disconnected" << std::endl;
    }
}

void IPCServer::handle_client(int client_fd) {
    uint8_t buffer[IPC_MAX_MESSAGE_SIZE];

    while (running_.load()) {
        // Read message header
        if (!recv_from_client(client_fd, buffer, IPC_HEADER_SIZE)) {
            break;
        }

        MessageHeader* header = reinterpret_cast<MessageHeader*>(buffer);

        // Validate header
        if (header->version != IPC_PROTOCOL_VERSION) {
            std::cerr << "Invalid protocol version: " << (int)header->version << std::endl;
            break;
        }

        if (header->payload_length > IPC_MAX_MESSAGE_SIZE - IPC_HEADER_SIZE) {
            std::cerr << "Payload too large: " << header->payload_length << std::endl;
            break;
        }

        // Read payload if present
        if (header->payload_length > 0) {
            if (!recv_from_client(client_fd, buffer + IPC_HEADER_SIZE, header->payload_length)) {
                break;
            }
        }

        // Invoke callback
        if (command_callback_) {
            command_callback_(header->message_type, buffer + IPC_HEADER_SIZE, header->payload_length);
        }
    }
}

bool IPCServer::send_message(uint8_t msg_type, const void* payload, uint16_t payload_len) {
    if (client_fd_ < 0) {
        return false; // No client connected
    }

    std::lock_guard<std::mutex> lock(send_mutex_);

    // Build header
    MessageHeader header;
    header.version = IPC_PROTOCOL_VERSION;
    header.message_type = msg_type;
    header.payload_length = payload_len;
    header.sequence_number = sequence_number_++;
    header.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();

    // Send header
    if (!send_to_client(client_fd_, reinterpret_cast<uint8_t*>(&header), IPC_HEADER_SIZE)) {
        return false;
    }

    // Send payload if present
    if (payload_len > 0 && payload != nullptr) {
        if (!send_to_client(client_fd_, static_cast<const uint8_t*>(payload), payload_len)) {
            return false;
        }
    }

    return true;
}

void IPCServer::set_command_callback(MessageCallback callback) {
    command_callback_ = callback;
}

bool IPCServer::send_to_client(int fd, const uint8_t* data, size_t len) {
    size_t total_sent = 0;
    while (total_sent < len) {
        ssize_t sent = send(fd, data + total_sent, len - total_sent, MSG_NOSIGNAL);
        if (sent < 0) {
            std::cerr << "Send failed: " << strerror(errno) << std::endl;
            return false;
        }
        total_sent += sent;
    }
    return true;
}

bool IPCServer::recv_from_client(int fd, uint8_t* buffer, size_t len) {
    size_t total_received = 0;
    while (total_received < len) {
        ssize_t received = recv(fd, buffer + total_received, len - total_received, 0);
        if (received <= 0) {
            if (received < 0) {
                std::cerr << "Receive failed: " << strerror(errno) << std::endl;
            }
            return false;
        }
        total_received += received;
    }
    return true;
}
