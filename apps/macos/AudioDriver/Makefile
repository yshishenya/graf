CXX ?= clang++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Werror
BUILD_DIR ?= .build/proof
PROOF_BIN := $(BUILD_DIR)/audio-driver-proof
PROOF_SOURCES := \
	Sources/Proof/ProofRunner.cpp \
	Sources/Proof/VirtualDeviceProof.cpp \
	Sources/Proof/PassthroughTimingProof.cpp

.PHONY: proof-scaffold-build proof-scaffold-run clean

proof-scaffold-build: $(PROOF_BIN)

proof-scaffold-run: proof-scaffold-build
	@$(PROOF_BIN)

$(PROOF_BIN): $(PROOF_SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(PROOF_SOURCES) -o $(PROOF_BIN)

clean:
	rm -rf $(BUILD_DIR)
