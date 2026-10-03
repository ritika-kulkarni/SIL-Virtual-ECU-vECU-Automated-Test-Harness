#include <gtest/gtest.h>
extern "C" {
#include "CanIf.h"
#include "PduR.h"
}

class PduRTest : public ::testing::Test {
protected:
    void SetUp() override {
        CanIf_Init();
        PduR_Init();
    }
};

TEST_F(PduRTest, LookupKnownRoutes) {
    EXPECT_EQ(PduR_LookupCanId(4), 0x18FF1200u);
    EXPECT_EQ(PduR_LookupCanId(99), 0u);
}

TEST_F(PduRTest, TransmitAndIndicate) {
    PduR_PduType pdu{};
    pdu.pdu_id = 4;
    pdu.length = 4;
    pdu.data[0] = 1;
    pdu.data[1] = 2;
    pdu.data[2] = 3;
    pdu.data[3] = 4;
    ASSERT_TRUE(PduR_Transmit(&pdu));

    CanIf_FrameType frame{};
    ASSERT_TRUE(CanIf_Receive(&frame));
    PduR_PduType out{};
    ASSERT_TRUE(PduR_CanIfRxIndication(&frame, &out));
    EXPECT_EQ(out.pdu_id, 4);
    EXPECT_EQ(out.data[3], 4);
}

TEST_F(PduRTest, RejectOversizedPdu) {
    PduR_PduType pdu{};
    pdu.pdu_id = 4;
    pdu.length = 9;
    EXPECT_FALSE(PduR_Transmit(&pdu));
}
