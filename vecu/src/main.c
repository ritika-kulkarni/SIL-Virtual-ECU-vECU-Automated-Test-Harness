#include "CanIf.h"
#include "PduR.h"
#include "Com.h"
#include "J1939App.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

/*
 * Lightweight TCP control plane for the Python harness bridge.
 * Commands (line-based):
 *   PING -> PONG
 *   SIGNAL <name> <value>
 *   TP <len>
 *   BUSOFF
 *   RECOVER
 *   STATUS
 *   QUIT
 */

static void handle_client(int fd) {
    char buf[256];
    ssize_t n;

    while ((n = read(fd, buf, sizeof(buf) - 1)) > 0) {
        buf[n] = '\0';
        if (strncmp(buf, "PING", 4) == 0) {
            dprintf(fd, "PONG\n");
        } else if (strncmp(buf, "SIGNAL ", 7) == 0) {
            char name[64];
            unsigned value = 0;
            if (sscanf(buf + 7, "%63s %u", name, &value) == 2) {
                bool ok = Com_SendSignal(name, value);
                dprintf(fd, "%s\n", ok ? "OK" : "ERR");
            } else {
                dprintf(fd, "ERR\n");
            }
        } else if (strncmp(buf, "TP ", 3) == 0) {
            unsigned len = 0;
            sscanf(buf + 3, "%u", &len);
            if (len == 0 || len > 128) {
                dprintf(fd, "ERR\n");
            } else {
                uint8_t payload[128];
                for (unsigned i = 0; i < len; ++i) {
                    payload[i] = (uint8_t)(i & 0xFFu);
                }
                J1939_TpResult r = J1939App_SendTp(payload, (uint16_t)len, 3);
                dprintf(fd, "OK delivered=%d retries=%u bytes=%u\n",
                        r.delivered ? 1 : 0, r.retries, r.bytes_delivered);
            }
        } else if (strncmp(buf, "BUSOFF", 6) == 0) {
            CanIf_ForceBusOff();
            dprintf(fd, "OK\n");
        } else if (strncmp(buf, "RECOVER", 7) == 0) {
            CanIf_Recover();
            dprintf(fd, "OK\n");
        } else if (strncmp(buf, "STATUS", 6) == 0) {
            dprintf(fd, "STATUS %s tx=%u rx=%u\n",
                    CanIf_GetStatus() == CANIF_BUS_OFF ? "BUS_OFF" : "ONLINE",
                    CanIf_GetTxCount(), CanIf_GetRxCount());
        } else if (strncmp(buf, "QUIT", 4) == 0) {
            dprintf(fd, "BYE\n");
            break;
        } else {
            dprintf(fd, "ERR unknown\n");
        }
    }
}

int main(int argc, char** argv) {
    int port = 19000;
    int server_fd;
    struct sockaddr_in addr;

    if (argc > 1) {
        port = atoi(argv[1]);
    }

    CanIf_Init();
    PduR_Init();
    Com_Init();
    J1939App_Init();

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        return 1;
    }
    int yes = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons((uint16_t)port);

    if (bind(server_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        return 1;
    }
    if (listen(server_fd, 1) < 0) {
        perror("listen");
        return 1;
    }
    fprintf(stderr, "vecu_sim listening on 127.0.0.1:%d\n", port);

    for (;;) {
        int client = accept(server_fd, NULL, NULL);
        if (client < 0) {
            perror("accept");
            continue;
        }
        handle_client(client);
        close(client);
    }
    return 0;
}
