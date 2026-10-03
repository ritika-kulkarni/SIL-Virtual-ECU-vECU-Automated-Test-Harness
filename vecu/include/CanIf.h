#ifndef VECU_CANIF_H
#define VECU_CANIF_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint32_t can_id;
    uint8_t data[8];
    uint8_t dlc;
    bool is_extended;
} CanIf_FrameType;

typedef enum {
    CANIF_ONLINE = 0,
    CANIF_BUS_OFF = 1
} CanIf_StatusType;

void CanIf_Init(void);
bool CanIf_Transmit(const CanIf_FrameType* frame);
bool CanIf_Receive(CanIf_FrameType* frame);
CanIf_StatusType CanIf_GetStatus(void);
void CanIf_ForceBusOff(void);
void CanIf_Recover(void);
uint32_t CanIf_GetTxCount(void);
uint32_t CanIf_GetRxCount(void);

/* Test hooks: inject a frame into RX path */
bool CanIf_InjectRx(const CanIf_FrameType* frame);

#ifdef __cplusplus
}
#endif

#endif /* VECU_CANIF_H */
