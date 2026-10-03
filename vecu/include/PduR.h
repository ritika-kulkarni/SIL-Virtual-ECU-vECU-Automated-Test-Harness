#ifndef VECU_PDUR_H
#define VECU_PDUR_H

#include <stdint.h>
#include <stdbool.h>
#include "CanIf.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint16_t pdu_id;
    uint8_t data[64];
    uint16_t length;
} PduR_PduType;

void PduR_Init(void);
bool PduR_Transmit(const PduR_PduType* pdu);
bool PduR_CanIfRxIndication(const CanIf_FrameType* frame, PduR_PduType* out_pdu);
uint32_t PduR_LookupCanId(uint16_t pdu_id);

#ifdef __cplusplus
}
#endif

#endif /* VECU_PDUR_H */
