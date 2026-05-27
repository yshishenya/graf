CXX ?= clang++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Werror
BUILD_DIR ?= .build/proof
PROOF_BIN := $(BUILD_DIR)/audio-driver-proof
RUNTIME_PROBE_BIN := $(BUILD_DIR)/runtime-device-probe
PROOF_SOURCES := \
	Sources/Proof/ProofRunner.cpp \
	Sources/Proof/VirtualDeviceProof.cpp \
	Sources/Proof/PassthroughTimingProof.cpp
RUNTIME_PROBE_SOURCES := Sources/Proof/RuntimeDeviceProbe.cpp

.PHONY: proof-scaffold-build proof-scaffold-run proof-runtime-probe-build proof-runtime-probe-run clean

proof-scaffold-build: $(PROOF_BIN)

proof-scaffold-run: proof-scaffold-build
	@$(PROOF_BIN)

proof-runtime-probe-build: $(RUNTIME_PROBE_BIN)

proof-runtime-probe-run: proof-runtime-probe-build
	@$(RUNTIME_PROBE_BIN)

$(PROOF_BIN): $(PROOF_SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(PROOF_SOURCES) -o $(PROOF_BIN)

$(RUNTIME_PROBE_BIN): $(RUNTIME_PROBE_SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(RUNTIME_PROBE_SOURCES) -framework CoreAudio -framework CoreFoundation -o $(RUNTIME_PROBE_BIN)

clean:
	rm -rf $(BUILD_DIR)
