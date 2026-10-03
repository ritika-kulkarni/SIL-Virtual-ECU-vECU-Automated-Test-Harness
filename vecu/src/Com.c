#include "Com.h"
#include "PduR.h"
#include <string.h>

typedef struct {
    char name[32];
    uint32_t value;
    bool valid;
} Com_SignalType;

static Com_SignalType g_signals[8];

void Com_Init(void) {
    memset(g_signals, 0, sizeof(g_signals));
}

static Com_SignalType* find_or_alloc(const char* name) {
    for (unsigned i = 0; i < 8; ++i) {
        if (g_signals[i].valid && strncmp(g_signals[i].name, name, sizeof(g_signals[i].name)) == 0) {
            return &g_signals[i];
        }
    }
    for (unsigned i = 0; i < 8; ++i) {
        if (!g_signals[i].valid) {
            strncpy(g_signals[i].name, name, sizeof(g_signals[i].name) - 1u);
            g_signals[i].valid = true;
            return &g_signals[i];
        }
    }
    return NULL;
}

bool Com_SendSignal(const char* name, uint32_t value) {
    PduR_PduType pdu;
    Com_SignalType* sig;

    if (name == NULL) {
        return false;
    }
    sig = find_or_alloc(name);
    if (sig == NULL) {
        return false;
    }
    sig->value = value;
    memset(&pdu, 0, sizeof(pdu));
    pdu.pdu_id = 4u;
    pdu.length = 4u;
    pdu.data[0] = (uint8_t)((value >> 24) & 0xFFu);
    pdu.data[1] = (uint8_t)((value >> 16) & 0xFFu);
    pdu.data[2] = (uint8_t)((value >> 8) & 0xFFu);
    pdu.data[3] = (uint8_t)(value & 0xFFu);
    return PduR_Transmit(&pdu);
}

bool Com_ReceiveSignal(const char* name, uint32_t* value) {
    CanIf_FrameType frame;
    PduR_PduType pdu;
    Com_SignalType* sig;

    if (name == NULL || value == NULL) {
        return false;
    }
    if (!CanIf_Receive(&frame)) {
        return false;
    }
    if (!PduR_CanIfRxIndication(&frame, &pdu) || pdu.length < 4u) {
        return false;
    }
    *value = ((uint32_t)pdu.data[0] << 24) | ((uint32_t)pdu.data[1] << 16) |
             ((uint32_t)pdu.data[2] << 8) | (uint32_t)pdu.data[3];
    sig = find_or_alloc(name);
    if (sig != NULL) {
        sig->value = *value;
    }
    return true;
}

bool Com_SendRaw(uint16_t pdu_id, const uint8_t* data, uint16_t length) {
    PduR_PduType pdu;
    if (data == NULL || length == 0u || length > 8u) {
        return false;
    }
    memset(&pdu, 0, sizeof(pdu));
    pdu.pdu_id = pdu_id;
    pdu.length = length;
    memcpy(pdu.data, data, length);
    return PduR_Transmit(&pdu);
}
