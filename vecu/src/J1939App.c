#include "J1939App.h"
#include "Com.h"
#include "CanIf.h"
#include <string.h>

void J1939App_Init(void) {
    CanIf_Init();
    /* PduR/Com initialized by caller or main */
}

uint16_t J1939App_SegmentCount(uint16_t payload_len) {
    if (payload_len == 0u) {
        return 0u;
    }
    return (uint16_t)((payload_len + 6u) / 7u);
}

J1939_TpResult J1939App_SendTp(const uint8_t* payload, uint16_t length, uint8_t max_retries) {
    J1939_TpResult result;
    uint16_t packets;
    uint8_t attempt;
    uint8_t seq;
    uint8_t frame_data[8];

    memset(&result, 0, sizeof(result));
    if (payload == NULL || length == 0u) {
        return result;
    }

    packets = J1939App_SegmentCount(length);
    for (attempt = 0; attempt <= max_retries; ++attempt) {
        /* RTS via COM raw PDU 2 */
        frame_data[0] = 0x10;
        frame_data[1] = (uint8_t)(length & 0xFFu);
        frame_data[2] = (uint8_t)((length >> 8) & 0xFFu);
        frame_data[3] = (uint8_t)(packets & 0xFFu);
        frame_data[4] = 0xFF;
        frame_data[5] = 0x12;
        frame_data[6] = 0xFF;
        frame_data[7] = 0x00;
        if (!Com_SendRaw(2u, frame_data, 8u)) {
            result.retries = (uint16_t)(attempt + 1u);
            continue;
        }

        for (seq = 1; seq <= packets; ++seq) {
            uint16_t offset = (uint16_t)((seq - 1u) * 7u);
            uint16_t chunk = (uint16_t)((length - offset) > 7u ? 7u : (length - offset));
            memset(frame_data, 0, sizeof(frame_data));
            frame_data[0] = seq;
            memcpy(&frame_data[1], &payload[offset], chunk);
            if (!Com_SendRaw(3u, frame_data, 8u)) {
                result.retries = (uint16_t)(attempt + 1u);
                break;
            }
        }
        if (seq > packets) {
            result.delivered = true;
            result.bytes_delivered = length;
            result.retries = (uint16_t)attempt;
            return result;
        }
    }
    return result;
}

bool J1939App_HandleEngineRequest(uint32_t request_value, uint32_t* response) {
    if (response == NULL) {
        return false;
    }
    /* Simple decision logic for MC/DC-friendly branches */
    if (request_value == 0u) {
        *response = 0u;
        return false;
    }
    if (request_value < 1000u) {
        *response = request_value * 2u;
        return true;
    }
    if (request_value < 5000u) {
        *response = request_value + 100u;
        return true;
    }
    *response = 0xFFFFFFFFu;
    return false;
}
