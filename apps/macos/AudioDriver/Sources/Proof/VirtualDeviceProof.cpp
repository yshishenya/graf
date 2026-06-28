#include <string>
#include <vector>

namespace two_brain_rec::audio_proof {

struct VirtualDeviceExpectation {
    std::string display_name;
    std::string direction;
};

std::vector<VirtualDeviceExpectation> ExpectedMVPDevices() {
    return {
        {"GRAF Microphone", "input"},
        {"GRAF Speaker", "output"},
    };
}

bool HasExactlyMVPDevices(const std::vector<VirtualDeviceExpectation>& devices) {
    if (devices.size() != 2) {
        return false;
    }

    const auto expected = ExpectedMVPDevices();
    return devices[0].display_name == expected[0].display_name &&
           devices[0].direction == expected[0].direction &&
           devices[1].display_name == expected[1].display_name &&
           devices[1].direction == expected[1].direction;
}

}  // namespace two_brain_rec::audio_proof
