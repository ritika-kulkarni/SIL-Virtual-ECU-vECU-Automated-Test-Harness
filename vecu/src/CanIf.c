#include "CanIf.h"
#include <string.h>

#define CANIF_RX_DEPTH 32

static CanIf_FrameType g_rx_q[CANIF_RX_DEPTH];
static uint8_t g_rx_head;
static uint8_t g_rx_tail;
static CanIf_StatusType g_status;
static uint32_t g_tx_count;
static uint32_t g_rx_count;

void CanIf_Init(void) {
    g_rx_head = 0;
    g_rx_tail = 0;
    g_status = CANIF_ONLINE;
    g_tx_count = 0;
    g_rx_count = 0;
    memset(g_rx_q, 0, sizeof(g_rx_q));
}

static bool rx_full(void) {
    return (uint8_t)((g_rx_head + 1u) % CANIF_RX_DEPTH) == g_rx_tail;
}

static bool rx_empty(void) {
    return g_rx_head == g_rx_tail;
}

bool CanIf_Transmit(const CanIf_FrameType* frame) {
    if (frame == NULL) {
        return false;
    }
    if (g_status == CANIF_BUS_OFF) {
        return false;
    }
    /* Loopback for SIL */
    if (!rx_full()) {
        g_rx_q[g_rx_head] = *frame;
        g_rx_head = (uint8_t)((g_rx_head + 1u) % CANIF_RX_DEPTH);
    }
    g_tx_count++;
    return true;
}

bool CanIf_Receive(CanIf_FrameType* frame) {
    if (frame == NULL || rx_empty() || g_status == CANIF_BUS_OFF) {
        return false;
    }
    *frame = g_rx_q[g_rx_tail];
    g_rx_tail = (uint8_t)((g_rx_tail + 1u) % CANIF_RX_DEPTH);
    g_rx_count++;
    return true;
}

CanIf_StatusType CanIf_GetStatus(void) {
    return g_status;
}

void CanIf_ForceBusOff(void) {
    g_status = CANIF_BUS_OFF;
}

void CanIf_Recover(void) {
    g_status = CANIF_ONLINE;
}

uint32_t CanIf_GetTxCount(void) {
    return g_tx_count;
}

uint32_t CanIf_GetRxCount(void) {
    return g_rx_count;
}

bool CanIf_InjectRx(const CanIf_FrameType* frame) {
    if (frame == NULL || rx_full()) {
        return false;
    }
    g_rx_q[g_rx_head] = *frame;
    g_rx_head = (uint8_t)((g_rx_head + 1u) % CANIF_RX_DEPTH);
    return true;
}
