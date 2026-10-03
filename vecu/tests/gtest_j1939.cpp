#include <gtest/gtest.h>
extern "C" {
#include "CanIf.h"
#include "PduR.h"
#include "Com.h"
#include "J1939App.h"
}

class J1939Test : public ::testing::Test {
protected:
    void SetUp() override {
        CanIf_Init();
        PduR_Init();
        Com_Init();
        J1939App_Init();
    }
};

TEST_F(J1939Test, SegmentCount) {
    EXPECT_EQ(J1939App_SegmentCount(0), 0);
    EXPECT_EQ(J1939App_SegmentCount(7), 1);
    EXPECT_EQ(J1939App_SegmentCount(8), 2);
    EXPECT_EQ(J1939App_SegmentCount(40), 6);
}

TEST_F(J1939Test, SendTpDelivers) {
    uint8_t payload[40];
    for (int i = 0; i < 40; ++i) {
        payload[i] = static_cast<uint8_t>(i);
    }
    auto result = J1939App_SendTp(payload, 40, 3);
    EXPECT_TRUE(result.delivered);
    EXPECT_EQ(result.bytes_delivered, 40);
}

TEST_F(J1939Test, EngineRequestBranches) {
    uint32_t response = 0;
    EXPECT_FALSE(J1939App_HandleEngineRequest(0, &response));
    EXPECT_TRUE(J1939App_HandleEngineRequest(10, &response));
    EXPECT_EQ(response, 20u);
    EXPECT_TRUE(J1939App_HandleEngineRequest(2000, &response));
    EXPECT_EQ(response, 2100u);
    EXPECT_FALSE(J1939App_HandleEngineRequest(9000, &response));
}
