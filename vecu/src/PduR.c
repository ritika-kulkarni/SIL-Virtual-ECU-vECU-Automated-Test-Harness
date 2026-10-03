#include "PduR.h"
#include <string.h>

typedef struct {
    uint16_t pdu_id;
    uint32_t can_id;
} PduR_RouteType;

static const PduR_RouteType g_routes[] = {
    {1u, 0x18EAFF00u},
    {2u, 0x18ECFF00u},
    {3u, 0x18EBFF00u},
    {4u, 0x18FF1200u},
};

void PduR_Init(void) {
    /* static table */
}

uint32_t PduR_LookupCanId(uint16_t pdu_id) {
    for (unsigned i = 0; i < sizeof(g_routes) / sizeof(g_routes[0]); ++i) {
        if (g_routes[i].pdu_id == pdu_id) {
            return g_routes[i].can_id;
        }
    }
    return 0u;
}

bool PduR_Transmit(const PduR_PduType* pdu) {
    CanIf_FrameType frame;
    uint32_t can_id;

    if (pdu == NULL || pdu->length == 0u || pdu->length > 8u) {
        return false;
    }
    can_id = PduR_LookupCanId(pdu->pdu_id);
    if (can_id == 0u) {
        return false;
    }
    memset(&frame, 0, sizeof(frame));
    frame.can_id = can_id;
    frame.dlc = (uint8_t)pdu->length;
    frame.is_extended = true;
    memcpy(frame.data, pdu->data, pdu->length);
    return CanIf_Transmit(&frame);
}

bool PduR_CanIfRxIndication(const CanIf_FrameType* frame, PduR_PduType* out_pdu) {
    if (frame == NULL || out_pdu == NULL) {
        return false;
    }
    for (unsigned i = 0; i < sizeof(g_routes) / sizeof(g_routes[0]); ++i) {
        if (g_routes[i].can_id == frame->can_id) {
            out_pdu->pdu_id = g_routes[i].pdu_id;
            out_pdu->length = frame->dlc;
            memset(out_pdu->data, 0, sizeof(out_pdu->data));
            memcpy(out_pdu->data, frame->data, frame->dlc);
            return true;
        }
    }
    return false;
}
