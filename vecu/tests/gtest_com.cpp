#include <gtest/gtest.h>
extern "C" {
#include "CanIf.h"
#include "PduR.h"
#include "Com.h"
}

class ComTest : public ::testing::Test {
protected:
    void SetUp() override {
        CanIf_Init();
        PduR_Init();
        Com_Init();
    }
};

TEST_F(ComTest, SendAndReceiveSignal) {
    ASSERT_TRUE(Com_SendSignal("EngineSpeed", 1234u));
    uint32_t value = 0;
    ASSERT_TRUE(Com_ReceiveSignal("EngineSpeed", &value));
    EXPECT_EQ(value, 1234u);
}

TEST_F(ComTest, SendRaw) {
    uint8_t data[3] = {1, 2, 3};
    EXPECT_TRUE(Com_SendRaw(4, data, 3));
    EXPECT_FALSE(Com_SendRaw(4, data, 0));
    EXPECT_FALSE(Com_SendRaw(4, nullptr, 3));
}
