#ifndef VECU_J1939APP_H
#define VECU_J1939APP_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    bool delivered;
    uint16_t retries;
    uint16_t bytes_delivered;
} J1939_TpResult;

void J1939App_Init(void);
uint16_t J1939App_SegmentCount(uint16_t payload_len);
J1939_TpResult J1939App_SendTp(const uint8_t* payload, uint16_t length, uint8_t max_retries);
bool J1939App_HandleEngineRequest(uint32_t request_value, uint32_t* response);

#ifdef __cplusplus
}
#endif

#endif /* VECU_J1939APP_H */
