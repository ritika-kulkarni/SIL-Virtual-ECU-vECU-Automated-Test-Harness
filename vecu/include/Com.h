#ifndef VECU_COM_H
#define VECU_COM_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

void Com_Init(void);
bool Com_SendSignal(const char* name, uint32_t value);
bool Com_ReceiveSignal(const char* name, uint32_t* value);
bool Com_SendRaw(uint16_t pdu_id, const uint8_t* data, uint16_t length);

#ifdef __cplusplus
}
#endif

#endif /* VECU_COM_H */
