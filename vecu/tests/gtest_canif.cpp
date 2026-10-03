#include <gtest/gtest.h>
extern "C" {
#include "CanIf.h"
}

class CanIfTest : public ::testing::Test {
protected:
    void SetUp() override { CanIf_Init(); }
};

TEST_F(CanIfTest, TransmitReceiveLoopback) {
    CanIf_FrameType tx{};
    tx.can_id = 0x18FF1200u;
    tx.dlc = 2;
    tx.data[0] = 0xABu;
    tx.data[1] = 0xCDu;
    tx.is_extended = true;
    ASSERT_TRUE(CanIf_Transmit(&tx));

    CanIf_FrameType rx{};
    ASSERT_TRUE(CanIf_Receive(&rx));
    EXPECT_EQ(rx.can_id, tx.can_id);
    EXPECT_EQ(rx.data[0], 0xABu);
    EXPECT_EQ(CanIf_GetTxCount(), 1u);
    EXPECT_EQ(CanIf_GetRxCount(), 1u);
}

TEST_F(CanIfTest, BusOffBlocksTransmit) {
    CanIf_ForceBusOff();
    EXPECT_EQ(CanIf_GetStatus(), CANIF_BUS_OFF);
    CanIf_FrameType tx{};
    tx.can_id = 1;
    tx.dlc = 1;
    EXPECT_FALSE(CanIf_Transmit(&tx));
    CanIf_Recover();
    EXPECT_EQ(CanIf_GetStatus(), CANIF_ONLINE);
    EXPECT_TRUE(CanIf_Transmit(&tx));
}

TEST_F(CanIfTest, NullFrameRejected) {
    EXPECT_FALSE(CanIf_Transmit(nullptr));
    EXPECT_FALSE(CanIf_Receive(nullptr));
}
