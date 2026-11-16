#include "../../RecApp/Storage/ProtectedCustodyMetadata.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <algorithm>
#include <string>
#include <cstdio>
#include <limits>
#include <vector>
#include <cstdlib>
#include <new>

// Executable-only actual allocation cuts. The pure fixed-shape reader has no
// job/cancellation/Files contract; do not invent one in this hook.
namespace {
struct MigrationAllocationHook {
    bool active = false, hit = false;
    std::size_t calls = 0, failAt = 0;
};
thread_local MigrationAllocationHook migrationAllocation;
}
void* operator new(std::size_t bytes) {
    if (migrationAllocation.active && ++migrationAllocation.calls == migrationAllocation.failAt) {
        migrationAllocation.hit = true;
        migrationAllocation.failAt = 0;
        throw std::bad_alloc();
    }
    if (auto* memory = std::malloc(bytes ? bytes : 1)) return memory;
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept { std::free(memory); }
void operator delete(void* memory, std::size_t) noexcept { std::free(memory); }

using namespace graf::windows;
namespace {
const CustodyContext own = [] { CustodyContext c{{}, {}, CustodyRole::packageState};
    c.storeId.fill(0x11); c.objectId.fill(0x22); return c; }();
std::string ref(bool v2, bool live = true, std::string role = "canonical") {
    return "{\"role\":\"" + role + "\",\"object_id\":\"" + std::string(32, '3') +
        "\",\"binding\":\"" + (live ? "live" : "sealed") + "\",\"generation\":" +
        (live ? "null" : "7") + ",\"length\":" + (live ? "null" : "96") +
        ",\"sha256\":" + (live ? "null" : "\"" + std::string(64, '4') + "\"") +
        (v2 ? ",\"representation\":\"flat_v1\",\"container_id\":null,\"committed_extent\":null,\"root_ref\":null" : "") + "}";
}
std::string package(bool v2, std::string refs, std::string phase = "capturing", std::string reason = "", bool shortValue = false) {
    return "{\"schema\":\"graf.custody.package.v" + std::string(v2 ? "2" : "1") +
        "\",\"store_id\":\"" + std::string(32, '1') + "\",\"object_id\":\"" + std::string(32, '2') +
        "\",\"generation\":5,\"directory_id\":\"test-package\",\"phase\":\"" + phase +
        "\",\"reason\":\"" + reason + "\",\"short_recording_discarded\":" +
        (shortValue ? "true" : "false") + ",\"refs\":[" + refs + "]}";
}
std::string replace(std::string value, std::string_view from, std::string_view to) {
    const auto at = value.find(from); assert(at != std::string::npos);
    value.replace(at, from.size(), to); return value;
}
auto read(std::string_view value) { return readCustodyPackage(value, own, 5, "test-package"); }
void reject(std::string_view value) { const auto result = read(value); assert(!result.ok() && result.error == CustodyCodecError::invalidPlaintext); }
std::string serialized(const CustodyPackageValue& value) {
    const auto result = writeCustodyPackage(value, own, 5, "test-package"); assert(result.ok());
    return {result.value->begin(), result.value->end()};
}
void bootstrapTests(const CustodyContext& context, const CustodyId& queue) {
    const auto before = CustodyOwnedMemory::usedBytes();
    std::size_t accepted = 0, rejected = 0;
    const auto check = [&](std::string_view json, bool expected) {
        auto result = readCustodyBootstrap(json, context, 5, queue);
        assert(result.ok() == expected);
        if (expected) ++accepted;
        else { ++rejected; assert(!result.value && result.error == CustodyCodecError::invalidPlaintext); }
        return result;
    };
    const std::array<std::string, 9> fields{
        "\"schema\":\"graf.custody.bootstrap.v1\"", "\"store_id\":\"" + std::string(32, '1') + "\"",
        "\"object_id\":\"" + std::string(32, '2') + "\"", "\"generation\":5", "\"mode\":\"protected\"",
        "\"queue_object_id\":\"" + std::string(32, '3') + "\"", "\"transaction_id\":null",
        "\"subject\":null", "\"directory_id\":null"};
    const auto object = [](const auto& parts) {
        std::string json = "{"; bool first = true;
        for (const auto& part : parts) if (!part.empty()) { if (!first) json += ','; first = false; json += part; }
        return json + "}";
    };
    const auto emit = [&](const CustodyBootstrapValue& value, const CustodyContext& ownContext,
        std::uint64_t generation, const CustodyId& queueId) {
        auto bytes = writeCustodyBootstrap(value, ownContext, generation, queueId); assert(bytes.ok());
        return std::string(bytes.value->begin(), bytes.value->end());
    };
    const auto valid = object(fields);
    const auto decoded = check(valid, true);
    assert(emit(*decoded.value, context, 5, queue) == valid);
    for (const auto subject : {"queue", "package"}) {
        auto migration = fields;
        migration[4] = "\"mode\":\"migrating\"";
        migration[6] = "\"transaction_id\":\"" + std::string(32, '4') + "\"";
        migration[7] = "\"subject\":\"" + std::string(subject) + "\"";
        migration[8] = std::string("\"directory_id\":") + (std::string_view(subject) == "package" ? "\"Package_9-\"" : "null");
        const auto json = object(migration); auto value = check(json, true);
        assert(emit(*value.value, context, 5, queue) == json);
        assert(emit(*check(emit(*value.value, context, 5, queue), true).value, context, 5, queue) == json);
    }
    auto reversed = fields; std::reverse(reversed.begin(), reversed.end()); check(object(reversed), true);
    check(" \r\n\t" + valid + " \n", true);
    check(replace(valid, "\"schema\"", "\"sch\\u0065ma\""), true);
    check(replace(valid, std::string(32, '1'), "\\u0031" + std::string(31, '1')), true);
    auto migratingPackage = replace(replace(replace(replace(valid, "\"protected\"", "\"migrating\""),
        "\"transaction_id\":null", "\"transaction_id\":\"" + std::string(32, '4') + "\""),
        "\"subject\":null", "\"subject\":\"package\""), "\"directory_id\":null", "\"directory_id\":\"Package_9-\"");
    check(replace(migratingPackage, "Package", "P\\u0061ckage"), true);
    auto maxDirectory = replace(migratingPackage, "Package_9-", std::string(300, 'a'));
    assert(emit(*check(maxDirectory, true).value, context, 5, queue) == maxDirectory);
    for (std::size_t i = 0; i < fields.size(); ++i) {
        auto missing = fields; missing[i].clear(); check(object(missing), false);
        // Decode duplicate keys before comparing their field mask.
        auto duplicated = fields; const auto keyEnd = fields[i].find(':');
        const auto original = fields[i].substr(0, keyEnd);
        const char c = original[1]; const char digits[] = "0123456789abcdef";
        const auto escaped = "\"\\u00" + std::string(1, digits[static_cast<unsigned char>(c) >> 4]) +
            digits[static_cast<unsigned char>(c) & 15] + original.substr(2);
        duplicated[i] += "," + escaped + fields[i].substr(keyEnd); check(object(duplicated), false);
        for (const auto type : {"[]", "{}", "true", "0"}) {
            auto bad = fields; bad[i] = fields[i].substr(0, keyEnd+1) + type; check(object(bad), false);
        }
        if (i < 6) { auto bad = fields; bad[i] = fields[i].substr(0, keyEnd+1) + "null"; check(object(bad), false); }
    }
    for (const auto bad : {"schema_version", "SCHEMA", "unknown"})
        check(replace(valid, "\"schema\"", "\"" + std::string(bad) + "\""), false);
    check(replace(valid, "bootstrap.v1", "bootstrap.v2"), false);
    check(replace(valid, "{", "{\"extra\":null,"), false);
    for (const auto n : {"0","-1","01","5.0","5e0","18446744073709551616","\"5\""})
        check(replace(valid, "\"generation\":5", "\"generation\":" + std::string(n)), false);
    const auto maximum = (std::numeric_limits<std::uint64_t>::max)();
    auto maxGeneration = replace(valid, "\"generation\":5", "\"generation\":18446744073709551615");
    auto maxValue = readCustodyBootstrap(maxGeneration, context, maximum, queue); assert(maxValue.ok());
    assert(emit(*maxValue.value, context, maximum, queue) == maxGeneration);
    // Exhaustive cross-field combinations, including unknown enum strings.
    for (const auto mode : {"protected","migrating","unknown"}) for (const auto transaction : {false,true})
        for (const auto subject : {"null","queue","package","unknown"}) for (const auto name : {"null","","Pkg"}) {
            auto parts = fields; parts[4] = "\"mode\":\"" + std::string(mode) + "\"";
            parts[6] = std::string("\"transaction_id\":") + (transaction ? "\"" + std::string(32,'4') + "\"" : "null");
            parts[7] = std::string("\"subject\":") + (std::string_view(subject) == "null" ? "null" : "\"" + std::string(subject) + "\"");
            parts[8] = std::string("\"directory_id\":") + (std::string_view(name) == "null" ? "null" : "\"" + std::string(name) + "\"");
            const bool protectedForm = std::string_view(mode) == "protected" && !transaction && std::string_view(subject) == "null" && std::string_view(name) == "null";
            const bool migratingForm = std::string_view(mode) == "migrating" && transaction &&
                ((std::string_view(subject) == "queue" && std::string_view(name) == "null") ||
                 (std::string_view(subject) == "package" && std::string_view(name) == "Pkg"));
            auto value = check(object(parts), protectedForm || migratingForm);
            if (value.ok()) assert(emit(*value.value, context, 5, queue) == object(parts));
        }
    for (const auto& field : {fields[1],fields[2],fields[5]}) {
        for (const auto bad : {"", "ABABABABABABABABABABABABABABABAB", "g1111111111111111111111111111111", "1111111111111111111111111111111", "111111111111111111111111111111111"})
            check(replace(valid, field, field.substr(0, field.find(':')+1) + "\"" + bad + "\""), false);
    }
    for (const auto bad : {"", "x/y", "x\\u0000y", "x\\u00e9", "x\\ud800", "x\\q", "x\\n"})
        check(replace(migratingPackage, "Package_9-", bad), false);
    check(replace(migratingPackage, "Package_9-", std::string(301,'a')), false);
    check(replace(migratingPackage, "Package_9-", std::string("x") + '\xff'), false);
    check(replace(migratingPackage, "Package_9-", "x\xc3\xa9"), false);
    check("\xef\xbb\xbf" + valid, false); check(valid + "x", false);
    check(valid.substr(0, valid.size()-1) + ",}", false); check("/*x*/" + valid, false);
    check(replace(valid, "\"transaction_id\":null", "\"transaction_id\":\"" + std::string(32,'A') + "\""), false);
    auto mismatch = context; mismatch.storeId[0] ^= 1;
    assert(!readCustodyBootstrap(valid, mismatch, 5, queue).ok());
    mismatch = context; mismatch.objectId[0] ^= 1;
    assert(!readCustodyBootstrap(valid, mismatch, 5, queue).ok());
    mismatch = context; mismatch.role = CustodyRole::queue;
    assert(!readCustodyBootstrap(valid, mismatch, 5, queue).ok());
    assert(!readCustodyBootstrap(valid, context, 6, queue).ok());
    assert(!readCustodyBootstrap(valid, context, 0, queue).ok());
    auto otherQueue = queue; otherQueue[0] ^= 1;
    assert(!readCustodyBootstrap(valid, context, 5, otherQueue).ok());
    // No invented nonzero/unique-ID restriction; expected independent IDs bind.
    auto zeros = *decoded.value; zeros.context.storeId.fill(0); zeros.context.objectId.fill(0); zeros.queueObjectId.fill(0);
    const auto zeroJson = emit(zeros, zeros.context, 5, zeros.queueObjectId);
    assert(readCustodyBootstrap(zeroJson, zeros.context, 5, zeros.queueObjectId).ok());
    auto letters = zeros; letters.context.storeId.fill(0xab);
    const auto letterJson = emit(letters, letters.context, 5, letters.queueObjectId);
    assert(readCustodyBootstrap(replace(letterJson, "ab", "\\u0061b"), letters.context, 5, letters.queueObjectId).ok());
    auto padded = valid; padded.append(65536-padded.size(), ' '); check(padded, true); padded += ' '; check(padded, false);
    check("", false);
    const auto invalidWriter = [&](const CustodyBootstrapValue& value) {
        const auto result = writeCustodyBootstrap(value, context, 5, queue);
        assert(!result.ok() && !result.value && result.error == CustodyCodecError::invalidInput);
        assert(CustodyOwnedMemory::usedBytes() == before);
    };
    auto mutated = *decoded.value; mutated.schema = 2; invalidWriter(mutated);
    mutated = *decoded.value; mutated.mode = static_cast<CustodyBootstrapMode>(99); invalidWriter(mutated);
    mutated = *decoded.value; mutated.generation = 0; invalidWriter(mutated);
    mutated = *decoded.value; mutated.context.role = CustodyRole::queue; invalidWriter(mutated);
    mutated = *decoded.value; mutated.context.storeId[0] ^= 1; invalidWriter(mutated);
    mutated = *decoded.value; mutated.context.objectId[0] ^= 1; invalidWriter(mutated);
    mutated = *decoded.value; mutated.queueObjectId[0] ^= 1; invalidWriter(mutated);
    mutated = *decoded.value; mutated.transactionId = CustodyId{}; invalidWriter(mutated);
    mutated = *decoded.value; mutated.subject = CustodyMigrationSubject::queue; invalidWriter(mutated);
    mutated = *decoded.value; mutated.directory.emplace(); invalidWriter(mutated);
    mutated = *readCustodyBootstrap(migratingPackage, context, 5, queue).value;
    auto migrationValue = mutated;
    mutated.subject = static_cast<CustodyMigrationSubject>(99); invalidWriter(mutated);
    mutated = migrationValue; mutated.transactionId.reset(); invalidWriter(mutated);
    mutated = migrationValue; mutated.directory.reset(); invalidWriter(mutated);
    mutated = migrationValue; mutated.directory->fill('a'); invalidWriter(mutated); // All301 bytes, no terminator.
    mutated = migrationValue; mutated.directory->fill(0); invalidWriter(mutated);
    mutated = migrationValue; (*mutated.directory)[0] = '/'; invalidWriter(mutated);
    mutated = migrationValue; mutated.subject = CustodyMigrationSubject::queue; invalidWriter(mutated);
    assert(!writeCustodyBootstrap(*decoded.value, mismatch, 5, queue).ok());
    assert(!writeCustodyBootstrap(*decoded.value, context, 0, queue).ok());
    assert(!writeCustodyBootstrap(*decoded.value, context, 6, queue).ok());
    assert(!writeCustodyBootstrap(*decoded.value, context, 5, otherQueue).ok());
    CustodyAllocator<std::uint8_t> allocator;
    const auto pressureCount = CustodyOwnedMemory::limit - before;
    auto* pressure = allocator.allocate(pressureCount);
    assert(readCustodyBootstrap(valid, context, 5, queue).ok());
    const auto refused = writeCustodyBootstrap(*decoded.value, context, 5, queue);
    assert(!refused.ok() && !refused.value && refused.error == CustodyCodecError::allocationFailed);
    assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
    auto invalid = *decoded.value; invalid.mode = static_cast<CustodyBootstrapMode>(-1);
    assert(writeCustodyBootstrap(invalid, context, 5, queue).error == CustodyCodecError::invalidInput);
    assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
    allocator.deallocate(pressure, pressureCount);
    assert(CustodyOwnedMemory::usedBytes() == before);
    assert(emit(*decoded.value, context, 5, queue) == valid); // Retry after budget release.
    assert(CustodyOwnedMemory::usedBytes() == before);
    std::printf("BOOTSTRAP_CODEC_MATRIX accepted=%zu rejected=%zu cap=65536 allocation_refusal=1 retry=1\n", accepted, rejected);
}
void migrationTests(const std::string& birth, const CustodyContext& context, const CustodyId& transaction, unsigned schema = 1) {
    const auto before = CustodyOwnedMemory::usedBytes();
    std::size_t accepted = 0, rejected = 0;
    const auto object = [](const auto& parts) {
        std::string out = "{"; bool first = true;
        for (const auto& p : parts) if (!p.empty()) { if (!first) out += ','; first = false; out += p; }
        return out + "}";
    };
    const auto check = [&](std::string_view json, bool expected, std::uint64_t generation = 2,
        CustodyMigrationSubject subject = CustodyMigrationSubject::queue, std::string_view name = "") {
        auto result = readCustodyMigration(json, context, generation, transaction, subject, name);
        assert(result.ok() == expected);
        if (expected) ++accepted;
        else { ++rejected; assert(!result.value && result.error == CustodyCodecError::invalidPlaintext); }
        return result;
    };
    const auto emit = [&](const CustodyMigrationValue& v) {
        const auto name = v.directory ? std::string_view(v.directory->data()) : std::string_view{};
        auto result = writeCustodyMigration(v, context, v.generation, transaction, v.subject, name); assert(result.ok());
        return std::string(result.value->begin(), result.value->end());
    };
    const std::array<std::string, 4> anchor{"\"object_id\":null","\"generation\":null","\"length\":3","\"sha256\":\"" + std::string(64,'6') + "\""};
    std::vector<std::string> source{"\"source\":\"ledger\"","\"source_length\":3","\"source_sha256\":\"" + std::string(64,'6') + "\"",
        "\"destination_object_id\":\"" + std::string(32,'5') + "\"","\"destination_generation\":null","\"destination_length\":null","\"destination_sha256\":null"};
    if (schema == 2) source.insert(source.end(), {"\"destination_representation\":\"flat_v1\"",
        "\"destination_container_id\":null", "\"destination_committed_extent\":null", "\"destination_root_ref\":null"});
    const std::array<std::string, 5> barrier{"\"object_id\":\"" + std::string(32,'2') + "\"","\"generation\":1","\"block_version\":9","\"envelope_bytes\":512","\"sha256\":\"" + std::string(64,'8') + "\""};
    const std::array<std::string, 6> authorization{"\"kind\":\"owner_confirmation\"","\"operation_id\":\"" + std::string(32,'4') + "\"",
        "\"actor_user_id\":\"actor\"","\"workspace_id\":\"space\"","\"queue_object_id\":\"" + std::string(32,'3') + "\"","\"queue_generation\":7"};
    const std::array<std::string, 12> root{"\"schema\":\"graf.custody.migration.v" + std::to_string(schema) + "\"","\"store_id\":\"" + std::string(32,'1') + "\"",
        "\"object_id\":\"" + std::string(32,'2') + "\"","\"generation\":2","\"transaction_id\":\"" + std::string(32,'4') + "\"",
        "\"subject\":\"queue\"","\"directory_id\":null","\"stage\":\"prepared\"","\"ledger_anchor\":" + object(anchor),
        "\"sources\":[" + object(source) + "]","\"barrier\":null","\"cleanup_authorization\":null"};
    const auto valid = object(root); const auto parsed = check(valid, true); assert(emit(*parsed.value) == valid);
    assert(emit(*check(birth, true, 1).value) == birth);
    std::array<std::string, 2> switched{};
    std::array<CustodyMigrationValue, 2> switchedValues{};
    for (unsigned subject = 0; subject < 2; ++subject) for (unsigned stage = 0; stage < 5; ++stage) {
        constexpr std::array<std::string_view, 5> stages{"prepared","copied_verified","switched","cleanup_pending","complete"};
        auto parts = root; auto a = anchor; auto s = source;
        const auto kind = subject ? CustodyMigrationSubject::package : CustodyMigrationSubject::queue;
        const std::string name = subject ? "Pkg" : "";
        if (subject) {
            parts[5] = "\"subject\":\"package\""; parts[6] = "\"directory_id\":\"Pkg\"";
            a[0] = "\"object_id\":\"" + std::string(32,'3') + "\""; a[1] = "\"generation\":7";
            s[0] = "\"source\":\"manifest\"";
        }
        parts[7] = "\"stage\":\"" + std::string(stages[stage]) + "\""; parts[8] = "\"ledger_anchor\":" + object(a);
        if (stage) { s[4] = "\"destination_generation\":7"; s[5] = "\"destination_length\":3"; s[6] = "\"destination_sha256\":\"" + std::string(64,'6') + "\""; }
        parts[9] = "\"sources\":[" + object(s) + "]";
        if (stage >= 2) parts[10] = "\"barrier\":" + object(barrier);
        if (stage >= 3) parts[11] = "\"cleanup_authorization\":" + object(authorization);
        const auto json = object(parts); auto value = check(json, true, 2, kind, name); assert(emit(*value.value) == json);
        assert(emit(*check(emit(*value.value), true, 2, kind, name).value) == json);
        if (stage == 2) { switched[subject] = json; switchedValues[subject] = *value.value; }
        if (stage) check(replace(json, "\"generation\":2", "\"generation\":1"), false, 1, kind, name);
        if (stage >= 2) check(replace(json, object(barrier), "null"), false, 2, kind, name);
        if (stage >= 3) check(replace(json, object(authorization), "null"), false, 2, kind, name);
        if (!stage) check(replace(json, "\"destination_generation\":null", "\"destination_generation\":7"), false, 2, kind, name);
        else for (const auto field : {"destination_generation","destination_length","destination_sha256"}) {
            const auto at = object(s).find("\"" + std::string(field) + "\":");
            const auto end = object(s).find_first_of(",}", at);
            check(replace(json, object(s).substr(at,end-at), "\"" + std::string(field) + "\":null"), false, 2, kind, name);
        }
    }
    // Every key in every closed object: omission, normalized duplicate, unknown and wrong types.
    const auto stress = [&](const auto& fields, auto wrap, bool packageSubject = false) {
        const auto refuse = [&](const auto& json) { check(json, false, 2,
            packageSubject ? CustodyMigrationSubject::package : CustodyMigrationSubject::queue, packageSubject ? "Pkg" : ""); };
        for (std::size_t i = 0; i < fields.size(); ++i) {
            auto bad = fields; bad[i].clear(); refuse(wrap(object(bad)));
            bad = fields; const auto colon = fields[i].find(':'); const char c = fields[i][1]; const char digits[] = "0123456789abcdef";
            const std::string escaped = "\"\\u00" + std::string(1,digits[static_cast<unsigned char>(c)>>4]) +
                digits[static_cast<unsigned char>(c)&15] + fields[i].substr(2);
            bad[i] += "," + escaped; refuse(wrap(object(bad)));
            for (const auto type : {"[]","{}","true","-1","01","1.0","1e0","18446744073709551616"}) {
                bad = fields; bad[i] = fields[i].substr(0,colon+1) + type; refuse(wrap(object(bad)));
            }
            if (fields[i].substr(colon+1) != "null") {
                bad = fields; bad[i] = fields[i].substr(0,colon+1) + "null"; refuse(wrap(object(bad)));
            }
            bad = fields; bad[i] = "\"alias_" + fields[i].substr(1); refuse(wrap(object(bad)));
        }
        refuse(wrap(replace(object(fields), "{", "{\"unknown\":null,")));
    };
    stress(root, [](const auto& x) { return x; });
    stress(anchor, [&](const auto& x) { return replace(valid,object(anchor),x); });
    stress(source, [&](const auto& x) { return replace(valid,object(source),x); });
    stress(barrier, [&](const auto& x) { return replace(switched[0],object(barrier),x); });
    const auto authorized = replace(switched[0], "\"cleanup_authorization\":null", "\"cleanup_authorization\":" + object(authorization));
    check(authorized, true);
    check(replace(valid,"\"cleanup_authorization\":null","\"cleanup_authorization\":" + object(authorization)),true);
    check(replace(birth,"\"barrier\":null","\"barrier\":" + object(barrier)),false,1);
    check(replace(birth,"\"cleanup_authorization\":null","\"cleanup_authorization\":" + object(authorization)),false,1);
    stress(authorization, [&](const auto& x) { return replace(authorized,object(authorization),x); });
    for (bool copied : {false,true}) for (unsigned mask=0;mask<8;++mask) {
        auto s=source; auto r=root;
        if (copied) r[7]="\"stage\":\"copied_verified\"";
        if (mask&1) s[4]="\"destination_generation\":7";
        if (mask&2) s[5]="\"destination_length\":3";
        if (mask&4) s[6]="\"destination_sha256\":\"" + std::string(64,'6') + "\"";
        r[9]="\"sources\":["+object(s)+"]";
        check(object(r),mask==(copied?7U:0U));
    }
    for (std::size_t i = 0; i < root.size(); ++i) if (i != 6 && i != 10 && i != 11) {
        auto bad = root; bad[i] = root[i].substr(0,root[i].find(':')+1) + "null"; check(object(bad), false);
    }
    check(replace(valid, "\"schema\"", "\"schema_version\""), false);
    check(replace(valid, schema == 1 ? "migration.v1" : "migration.v2", schema == 1 ? "migration.v2" : "migration.v1"), false);
    auto reversed = root; std::reverse(reversed.begin(),reversed.end()); check(object(reversed), true);
    auto reversedSource = source; std::reverse(reversedSource.begin(), reversedSource.end());
    check(replace(object(reversed), object(source), object(reversedSource)), true); // Sources before schema, both orders arbitrary.
    check(" \r\n\t" + valid + " \n", true); check(replace(valid,"\"schema\"","\"sch\\u0065ma\""), true);
    check(replace(valid,std::string(32,'1'),"\\u0031" + std::string(31,'1')), true);
    for (const auto bad : {"", "G11111111111111111111111111111111", "ABABABABABABABABABABABABABABABAB", "1111111111111111111111111111111"})
        check(replace(valid,std::string(32,'1'),bad), false);
    check(replace(valid,std::string(64,'6'),std::string(63,'6')), false);
    check(replace(valid,std::string(64,'6'),std::string(64,'A')), false);
    check(replace(valid,"\"generation\":2","\"generation\":0"), false);
    check(replace(valid,"\"source_length\":3","\"source_length\":4"), false);
    check(replace(valid,"\"source_sha256\":\"" + std::string(64,'6') + "\"","\"source_sha256\":\"" + std::string(64,'7') + "\""), false);
    check(replace(switched[0],"\"destination_generation\":7","\"destination_generation\":0"),false);
    check(replace(switched[0],"\"destination_length\":3","\"destination_length\":4"),false);
    check(replace(switched[0],"\"destination_sha256\":\"" + std::string(64,'6') + "\"","\"destination_sha256\":\"" + std::string(64,'7') + "\""),false);
    check(replace(valid,"\"source\":\"ledger\"","\"source\":\"manifest\""), false);
    check(replace(valid,"\"source\":\"ledger\"","\"source\":\"unknown\""), false);
    check(replace(valid,"[" + object(source) + "]","[]"), false);
    check(replace(valid,"[" + object(source) + "]","[" + object(source) + "," + object(source) + "]"), false);
    std::string seven = "["; for (unsigned i=0;i<7;++i) { if(i) seven += ','; seven += object(source); } seven += ']';
    check(replace(valid,"[" + object(source) + "]",seven), false);
    check(replace(valid,"\"object_id\":null","\"object_id\":\"" + std::string(32,'3') + "\""), false);
    check(replace(valid,"\"generation\":null","\"generation\":7"), false);
    auto protectedAnchor = replace(replace(valid,"\"object_id\":null","\"object_id\":\"" + std::string(32,'3') + "\""),"\"generation\":null","\"generation\":7");
    check(protectedAnchor, true); check(replace(protectedAnchor,"\"generation\":7","\"generation\":0"), false);
    for (const auto n : {"0","2","18446744073709551615"}) check(replace(switched[0],"\"generation\":1","\"generation\":" + std::string(n)), false);
    for (const auto n : {"0"}) check(replace(switched[0],"\"block_version\":9","\"block_version\":" + std::string(n)), false);
    for (const auto n : {"16","69633"}) check(replace(switched[0],"\"envelope_bytes\":512","\"envelope_bytes\":" + std::string(n)), false);
    for (const auto n : {"17","69632"}) check(replace(switched[0],"\"envelope_bytes\":512","\"envelope_bytes\":" + std::string(n)), true);
    check(replace(switched[0],object(barrier),replace(object(barrier),std::string(32,'2'),std::string(32,'3'))), false);
    check(replace(authorized,"\"kind\":\"owner_confirmation\"","\"kind\":\"unknown\""), false);
    check(replace(authorized,"\"operation_id\":\"" + std::string(32,'4') + "\"","\"operation_id\":\"other\""), false);
    check(replace(authorized,"\"kind\":\"owner_confirmation\"","\"kind\":\"delete_purge\""), true);
    check(replace(replace(authorized,"\"kind\":\"owner_confirmation\"","\"kind\":\"delete_purge\""),"\"operation_id\":\"" + std::string(32,'4') + "\"","\"operation_id\":\"delete-op\""), true);
    check(replace(authorized,"\"queue_generation\":7","\"queue_generation\":0"), false);
    for (const auto name : {"","x/y","x\\u0000y","x\\u00e9","x\\ud800","x\\q"}) check(replace(authorized,"\"actor_user_id\":\"actor\"","\"actor_user_id\":\"" + std::string(name) + "\""), false);
    check(replace(authorized,"\"actor_user_id\":\"actor\"","\"actor_user_id\":\"" + std::string(300,'a') + "\""), true);
    check(replace(authorized,"\"actor_user_id\":\"actor\"","\"actor_user_id\":\"" + std::string(301,'a') + "\""), false);
    check("\xef\xbb\xbf" + valid,false); check(valid + "x",false); check("/*x*/" + valid,false);
    check(valid.substr(0,valid.size()-1) + ",}",false);
    check(replace(valid,"prepared",std::string("pre") + '\xff'),false);
    check("",false); check(replace(valid,"prepared","pre\\q"),false);
    auto padded=valid; padded.append(65536-padded.size(),' '); check(padded,true); padded+=' '; check(padded,false);
    auto value = *parsed.value;
    const auto invalid = [&](const CustodyMigrationValue& v) {
        auto result=writeCustodyMigration(v,context,2,transaction,CustodyMigrationSubject::queue,"");
        assert(!result.ok() && !result.value && result.error==CustodyCodecError::invalidInput);
        assert(CustodyOwnedMemory::usedBytes()==before);
    };
    auto bad=value; bad.stage=static_cast<CustodyMigrationStage>(99); invalid(bad);
    bad=value; bad.subject=static_cast<CustodyMigrationSubject>(99); invalid(bad);
    bad=value; bad.sources[0].kind=static_cast<CustodyMigrationSourceKind>(99); invalid(bad);
    bad=value; bad.sourceCount=7; invalid(bad); bad.sourceCount=0; invalid(bad);
    bad=value; bad.schema=3; invalid(bad); bad=value; bad.generation=0; invalid(bad);
    bad=value; bad.sources[0].length++; invalid(bad);
    bad=value; bad.authorization=CustodyCleanupAuthorization{}; bad.authorization->kind=static_cast<CustodyCleanupKind>(99); invalid(bad);
    for (unsigned component=0;component<3;++component) {
        auto other=context; if(component==0) other.storeId[0]^=1; else if(component==1) other.objectId[0]^=1; else other.role=CustodyRole::queue;
        assert(!readCustodyMigration(valid,other,2,transaction,CustodyMigrationSubject::queue,"").ok());
        assert(!writeCustodyMigration(value,other,2,transaction,CustodyMigrationSubject::queue,"").ok());
    }
    auto otherTransaction=transaction; otherTransaction[0]^=1;
    assert(!readCustodyMigration(valid,context,2,otherTransaction,CustodyMigrationSubject::queue,"").ok());
    assert(!writeCustodyMigration(value,context,2,otherTransaction,CustodyMigrationSubject::queue,"").ok());
    assert(!readCustodyMigration(valid,context,3,transaction,CustodyMigrationSubject::queue,"").ok());
    assert(!writeCustodyMigration(value,context,3,transaction,CustodyMigrationSubject::queue,"").ok());
    assert(!readCustodyMigration(valid,context,2,transaction,CustodyMigrationSubject::package,"Pkg").ok());
    assert(!readCustodyMigration(valid,context,2,transaction,CustodyMigrationSubject::queue,"Pkg").ok());
    assert(!readCustodyMigration(switched[1],context,2,transaction,CustodyMigrationSubject::package,"Other").ok());
    const auto maximum=(std::numeric_limits<std::uint64_t>::max)();
    auto maxJson=replace(valid,"\"generation\":2","\"generation\":18446744073709551615");
    auto maxValue=readCustodyMigration(maxJson,context,maximum,transaction,CustodyMigrationSubject::queue,""); assert(maxValue.ok()); assert(emit(*maxValue.value)==maxJson);
    // Independent struct mutations cover role caps and writer stage boundaries.
    auto packageValue=switchedValues[1]; packageValue.stage=CustodyMigrationStage::prepared; packageValue.barrier.reset();
    packageValue.sources[0].destinationGeneration.reset(); packageValue.sources[0].destinationLength.reset(); packageValue.sources[0].destinationSha256.reset();
    const auto packagePrepared=emit(packageValue);
    check(replace(packagePrepared,"\"object_id\":\"" + std::string(32,'3') + "\"","\"object_id\":null"),false,2,CustodyMigrationSubject::package,"Pkg");
    check(replace(replace(packagePrepared,"\"object_id\":\"" + std::string(32,'3') + "\"","\"object_id\":null"),"\"generation\":7","\"generation\":null"),false,2,CustodyMigrationSubject::package,"Pkg");
    check(replace(packagePrepared,"\"source\":\"manifest\"","\"source\":\"ledger\""),false,2,CustodyMigrationSubject::package,"Pkg");
    for (const auto badName : {"","x/y","x\\u0000y","x\\ud800","x\\u00e9"}) {
        assert(!readCustodyMigration(replace(packagePrepared,"\"Pkg\"","\""+std::string(badName)+"\""),context,2,transaction,CustodyMigrationSubject::package,badName).ok());
    }
    const std::string name300(300,'a');
    auto name300json=replace(packagePrepared,"\"Pkg\"","\""+name300+"\"");
    auto name300value=readCustodyMigration(name300json,context,2,transaction,CustodyMigrationSubject::package,name300); assert(name300value.ok()); assert(emit(*name300value.value)==name300json);
    const std::string name301(301,'a');
    assert(!readCustodyMigration(replace(packagePrepared,"\"Pkg\"","\""+name301+"\""),context,2,transaction,CustodyMigrationSubject::package,name301).ok());
    auto allSources=packageValue; allSources.sourceCount=5;
    for (unsigned i=0;i<5;++i) { allSources.sources[i]=packageValue.sources[0]; allSources.sources[i].kind=static_cast<CustodyMigrationSourceKind>(i+1); }
    const auto canonicalSources=emit(allSources); check(canonicalSources,true,2,CustodyMigrationSubject::package,"Pkg");
    std::reverse(allSources.sources.begin(),allSources.sources.begin()+allSources.sourceCount);
    assert(emit(allSources)==canonicalSources);
    allSources.sources[1].kind=allSources.sources[0].kind;
    assert(writeCustodyMigration(allSources,context,2,transaction,CustodyMigrationSubject::package,"Pkg").error==CustodyCodecError::invalidInput);
    auto noTerminator=packageValue; noTerminator.directory->fill('a');
    assert(writeCustodyMigration(noTerminator,context,2,transaction,CustodyMigrationSubject::package,"Pkg").error==CustodyCodecError::invalidInput);
    assert(!writeCustodyMigration(packageValue,context,2,transaction,CustodyMigrationSubject::package,"Other").ok());
    assert(!writeCustodyMigration(value,context,2,transaction,CustodyMigrationSubject::package,"Pkg").ok());
    assert(!writeCustodyMigration(value,context,2,transaction,CustodyMigrationSubject::queue,"Pkg").ok());
    {
        auto zeroValue=value; zeroValue.context.storeId.fill(0); zeroValue.context.objectId.fill(0); zeroValue.transactionId.fill(0); zeroValue.sources[0].destinationObjectId.fill(0);
        auto bytes=writeCustodyMigration(zeroValue,zeroValue.context,2,zeroValue.transactionId,CustodyMigrationSubject::queue,""); assert(bytes.ok());
        assert(readCustodyMigration({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},zeroValue.context,2,zeroValue.transactionId,CustodyMigrationSubject::queue,"").ok());
    }
    for (const auto kind : {CustodyMigrationSourceKind::manifest,CustodyMigrationSourceKind::canonical,CustodyMigrationSourceKind::media,CustodyMigrationSourceKind::playback,CustodyMigrationSourceKind::recovery}) {
        auto& s=packageValue.sources[0]; s.kind=kind; s.destinationGeneration.reset(); s.destinationLength.reset(); s.destinationSha256.reset();
        s.length=(kind==CustodyMigrationSourceKind::manifest || kind==CustodyMigrationSourceKind::recovery) ? 65536 : (std::uint64_t{64}<<30);
        check(emit(packageValue),true,2,CustodyMigrationSubject::package,"Pkg");
        ++s.length;
        assert(writeCustodyMigration(packageValue,context,2,transaction,CustodyMigrationSubject::package,"Pkg").error==CustodyCodecError::invalidInput);
    }
    auto largeLedger=value; largeLedger.anchor.length=largeLedger.sources[0].length=4*1024*1024; check(emit(largeLedger),true);
    ++largeLedger.anchor.length; ++largeLedger.sources[0].length; invalid(largeLedger);
    for (unsigned extra = 0; extra < 4; ++extra) {
        auto typed = value; typed.schema = 1;
        auto& s = typed.sources[0];
        if (extra == 0) s.destinationPacked = true;
        if (extra == 1) s.destinationContainerId = CustodyId{};
        if (extra == 2) s.destinationCommittedExtent = ProtectedPackedCustodyFormat::appendOffset;
        if (extra == 3) s.destinationRootRef = ProtectedPackedCustodyFormat::Reference{};
        invalid(typed); // Schema1 cannot silently discard ANY typed v2 extra.
    }
    if (schema == 1) {
        for (const auto extra : {"\"destination_representation\":\"flat_v1\"", "\"destination_container_id\":null",
            "\"destination_committed_extent\":null", "\"destination_root_ref\":null"})
            check(replace(valid, object(source), replace(object(source), "}", "," + std::string(extra) + "}")), false);
    } else {
        using Format = ProtectedPackedCustodyFormat;
        const auto hexText = [](const auto& bytes) {
            std::string out; for (auto b : bytes) { out += "0123456789abcdef"[b >> 4]; out += "0123456789abcdef"[b & 15]; } return out;
        };
        auto prepared = switchedValues[1]; prepared.stage = CustodyMigrationStage::prepared; prepared.barrier.reset();
        auto& s = prepared.sources[0]; s.kind = CustodyMigrationSourceKind::media; s.length = 96;
        s.destinationGeneration.reset(); s.destinationLength.reset(); s.destinationSha256.reset();
        s.destinationPacked = true; s.destinationContainerId = CustodyId{}; s.destinationContainerId->fill(0x55);
        const auto verify = [&](const CustodyMigrationValue& v, bool expected = true) {
            const auto name = v.subject == CustodyMigrationSubject::queue ? "" : "Pkg";
            auto bytes = writeCustodyMigration(v, context, v.generation, transaction, v.subject, name);
            assert(bytes.ok() == expected);
            if (!expected) { assert(!bytes.value && bytes.error == CustodyCodecError::invalidInput); return std::string{}; }
            const std::string json(bytes.value->begin(), bytes.value->end());
            auto decoded = check(json, true, v.generation, v.subject, name);
            assert(emit(*decoded.value) == json);
            const auto& a = decoded.value->sources[0]; const auto& b = v.sources[0];
            assert(decoded.value->schema == 2 && a.destinationPacked == b.destinationPacked &&
                a.destinationContainerId == b.destinationContainerId && a.destinationCommittedExtent == b.destinationCommittedExtent &&
                a.destinationRootRef == b.destinationRootRef);
            return json;
        };
        const auto preparedJson = verify(prepared);
        auto preparedBirth = prepared; preparedBirth.generation = 1; verify(preparedBirth);
        auto copied = prepared; copied.stage = CustodyMigrationStage::copiedVerified;
        auto& c = copied.sources[0]; c.destinationGeneration = 7; c.destinationLength = c.length; c.destinationSha256 = c.sha256;
        c.destinationCommittedExtent = Format::appendOffset + 128;
        const auto rootBytes = Format::encodeReference({PackedRecordKind::nodeL2, 128, Format::appendOffset, 7, 0, {}}); assert(rootBytes);
        c.destinationRootRef = *rootBytes;
        const auto copiedJson = verify(copied);
        const auto rejectPackage = [&](const std::string& json) { check(json, false, 2, CustodyMigrationSubject::package, "Pkg"); };
        rejectPackage(replace(preparedJson, "\"destination_container_id\":\"" + std::string(32,'5') + "\"", "\"destination_container_id\":null"));
        rejectPackage(replace(copiedJson, "\"destination_generation\":7", "\"destination_generation\":0"));
        rejectPackage(replace(copiedJson, "\"destination_length\":96", "\"destination_length\":97"));
        rejectPackage(replace(copiedJson, "\"destination_sha256\":\"" + std::string(64,'6') + "\"", "\"destination_sha256\":\"" + std::string(64,'7') + "\""));
        const std::array<std::string, 11> packedSource{"\"source\":\"media\"", "\"source_length\":96",
            "\"source_sha256\":\"" + std::string(64,'6') + "\"", "\"destination_object_id\":\"" + std::string(32,'5') + "\"",
            "\"destination_generation\":7", "\"destination_length\":96", "\"destination_sha256\":\"" + std::string(64,'6') + "\"",
            "\"destination_representation\":\"packed_v2\"", "\"destination_container_id\":\"" + std::string(32,'5') + "\"",
            "\"destination_committed_extent\":33024", "\"destination_root_ref\":\"" + hexText(*rootBytes) + "\""};
        assert(copiedJson.find(object(packedSource)) != std::string::npos);
        stress(packedSource, [&](const auto& x) { return replace(copiedJson, object(packedSource), x); }, true);
        auto reversedPacked = packedSource; std::reverse(reversedPacked.begin(), reversedPacked.end());
        auto permuted = replace(copiedJson, object(packedSource), object(reversedPacked));
        const auto schemaEnd = permuted.find(',');
        permuted = "{" + permuted.substr(schemaEnd+1, permuted.size()-schemaEnd-2) + "," + permuted.substr(1, schemaEnd-1) + "}";
        check(permuted, true, 2, CustodyMigrationSubject::package, "Pkg");
        rejectPackage(replace(copiedJson, "packed_v2", "unknown"));
        rejectPackage(replace(copiedJson, "migration.v2", "migration.v1"));
        rejectPackage(replace(copiedJson, "\"sources\":[", "\"sources\":[[[[["));
        rejectPackage("\xef\xbb\xbf" + copiedJson); rejectPackage(copiedJson + "x");
        for (const auto& badHex : {std::string(127,'0'), std::string(129,'0'), std::string(128,'A'), std::string(128,'g')})
            rejectPackage(replace(copiedJson, hexText(*rootBytes), badHex));
        for (const auto& badId : {std::string(31,'5'), std::string(33,'5'), std::string(32,'A')})
            rejectPackage(replace(copiedJson, packedSource[8], "\"destination_container_id\":\"" + badId + "\""));
        for (const auto n : {"-1", "01", "1.0", "1e0", "18446744073709551616"})
            rejectPackage(replace(copiedJson, packedSource[9], "\"destination_committed_extent\":" + std::string(n)));
        for (unsigned stage = 0; stage < 5; ++stage) for (unsigned kind = 1; kind <= 5; ++kind) {
            auto v = stage ? copied : prepared; v.stage = static_cast<CustodyMigrationStage>(stage);
            v.sources[0].kind = static_cast<CustodyMigrationSourceKind>(kind);
            if (stage >= 2) v.barrier = switchedValues[1].barrier;
            if (stage >= 3) {
                v.authorization = CustodyCleanupAuthorization{};
                v.authorization->kind = CustodyCleanupKind::deletePurge; v.authorization->queueGeneration = 7;
                for (auto* id : {&v.authorization->operationId, &v.authorization->actorUserId, &v.authorization->workspaceId}) id->at(0) = 'a';
            }
            verify(v, kind >= 2 && kind <= 4);
            if (kind == 1 || kind == 5) {
                const auto json = stage ? copiedJson : preparedJson;
                rejectPackage(replace(json, "\"source\":\"media\"", kind == 1 ? "\"source\":\"manifest\"" : "\"source\":\"recovery\""));
            }
        }
        // Mixed sources exercise all five package kinds and deterministic set order.
        auto mixed = copied; mixed.sourceCount = 5;
        for (unsigned i = 0; i < 5; ++i) {
            mixed.sources[i] = copied.sources[0]; auto& m = mixed.sources[i]; m.kind = static_cast<CustodyMigrationSourceKind>(i+1);
            if (i == 0 || i == 4) { m.destinationPacked = false; m.destinationContainerId.reset(); m.destinationCommittedExtent.reset(); m.destinationRootRef.reset(); }
        }
        const auto mixedJson = verify(mixed);
        std::reverse(mixed.sources.begin(), mixed.sources.begin()+mixed.sourceCount); assert(verify(mixed) == mixedJson);
        for (unsigned field = 0; field < 3; ++field) {
            auto v = value;
            if (field == 0) v.sources[0].destinationContainerId = CustodyId{};
            if (field == 1) v.sources[0].destinationCommittedExtent = Format::appendOffset;
            if (field == 2) v.sources[0].destinationRootRef = Format::Reference{};
            invalid(v); // Flat must reject each non-null stamp, not ignore it.
        }
        auto queuePacked = prepared; queuePacked.subject = CustodyMigrationSubject::queue; queuePacked.directory.reset();
        queuePacked.anchor.objectId.reset(); queuePacked.anchor.generation.reset(); queuePacked.anchor.length = s.length; queuePacked.anchor.sha256 = s.sha256;
        queuePacked.sources[0].kind = CustodyMigrationSourceKind::ledger; verify(queuePacked, false);
        for (bool isPrepared : {true, false}) for (unsigned mask = 0; mask < 32; ++mask) {
            auto v = isPrepared ? prepared : copied; auto& m = v.sources[0];
            m.destinationGeneration.reset(); m.destinationLength.reset(); m.destinationSha256.reset(); m.destinationCommittedExtent.reset(); m.destinationRootRef.reset();
            if (mask & 1) m.destinationGeneration = c.destinationGeneration;
            if (mask & 2) m.destinationLength = c.destinationLength;
            if (mask & 4) m.destinationSha256 = c.destinationSha256;
            if (mask & 8) m.destinationCommittedExtent = c.destinationCommittedExtent;
            if (mask & 16) m.destinationRootRef = c.destinationRootRef;
            verify(v, mask == (isPrepared ? 0U : 31U));
            auto fields = packedSource;
            for (unsigned bit = 0; bit < 5; ++bit) if (!(mask & (1U << bit))) {
                const auto at = bit < 3 ? 4+bit : 6+bit;
                fields[at] = fields[at].substr(0, fields[at].find(':')+1) + "null";
            }
            auto json = replace(copiedJson, object(packedSource), object(fields));
            if (isPrepared) json = replace(json, "copied_verified", "prepared");
            check(json, mask == (isPrepared ? 0U : 31U), 2, CustodyMigrationSubject::package, "Pkg");
        }
        auto missingContainer = prepared; missingContainer.sources[0].destinationContainerId.reset(); verify(missingContainer, false);
        missingContainer = copied; missingContainer.sources[0].destinationContainerId.reset(); verify(missingContainer, false);
        for (unsigned fault = 0; fault < 6; ++fault) {
            auto v = copied; auto& m = v.sources[0];
            if (fault == 0) m.destinationGeneration = 0;
            if (fault == 1) ++*m.destinationLength;
            if (fault == 2) m.destinationSha256->at(0) ^= 1;
            if (fault == 3) m.destinationGeneration = 1;
            if (fault == 4) m.length = *m.destinationLength = (std::uint64_t{64} << 30) + 1;
            if (fault == 5) m.destinationCommittedExtent = Format::appendOffset;
            verify(v, false);
        }
        // Mutate actual Ref64B wire bytes, not an encoder that already rejects bad values.
        const auto put = [](auto& bytes, std::size_t at, std::uint64_t n, unsigned width) {
            for (unsigned i = 0; i < width; ++i) bytes[at+i] = static_cast<std::uint8_t>(n >> (i*8));
        };
        for (unsigned fault = 0; fault < 16; ++fault) {
            auto v = copied; auto& r = *v.sources[0].destinationRootRef;
            if (fault < 5) put(r, 0, fault < 4 ? fault : 6, 4); // EMPTY/DATA/L0/L1/ZERO are not a nonempty root.
            if (fault == 5) put(r, 28, 1, 4);
            if (fault == 6) put(r, 24, 1, 4);
            if (fault == 7) put(r, 16, 0, 8);
            if (fault == 8) put(r, 16, 8, 8);
            if (fault == 9) put(r, 8, Format::appendOffset+1, 8);
            if (fault == 10) put(r, 8, (std::numeric_limits<std::uint64_t>::max)()-15, 8);
            if (fault == 11) put(r, 4, 16, 4);
            if (fault == 12) put(r, 4, 8193, 4);
            if (fault == 13) put(r, 0, 5, 4); // HEAD.
            if (fault == 14) put(r, 0, 99, 4);
            if (fault == 15) put(r, 8, Format::appendOffset-16, 8);
            verify(v, false);
            rejectPackage(replace(copiedJson, hexText(*rootBytes), hexText(r)));
        }
        auto empty = copied; auto& e = empty.sources[0]; e.length = 0; e.destinationLength = 0;
        e.destinationGeneration = 1; e.destinationCommittedExtent = Format::appendOffset; e.destinationRootRef = Format::Reference{};
        verify(empty); e.destinationCommittedExtent = Format::appendOffset+16; verify(empty, false);
        e.destinationGeneration = 2; verify(empty); // Later EMPTY roots may retain a larger committed extent.
        auto maximumPacked = copied; maximumPacked.generation = (std::numeric_limits<std::uint64_t>::max)();
        maximumPacked.sources[0].destinationGeneration = maximumPacked.generation;
        maximumPacked.sources[0].destinationCommittedExtent = maximumPacked.generation; verify(maximumPacked);
        auto paddedPacked = copiedJson; paddedPacked.append(65536-paddedPacked.size(), ' ');
        check(paddedPacked, true, 2, CustodyMigrationSubject::package, "Pkg"); paddedPacked += ' '; rejectPackage(paddedPacked);
        {
            CustodyAllocator<std::uint8_t> budget;
            const auto pressureBytes = CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes();
            auto* pressure = budget.allocate(pressureBytes);
            migrationAllocation = {true, false, 0, 0};
            const auto parsedAtQuota = readCustodyMigration(copiedJson, context, 2, transaction, CustodyMigrationSubject::package, "Pkg");
            migrationAllocation.active = false;
            assert(parsedAtQuota.ok() && parsedAtQuota.value->sources[0].destinationRootRef == c.destinationRootRef && migrationAllocation.calls == 0);
            const auto refused = writeCustodyMigration(copied, context, 2, transaction, CustodyMigrationSubject::package, "Pkg");
            assert(!refused.ok() && !refused.value && refused.error == CustodyCodecError::allocationFailed);
            assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
            budget.deallocate(pressure, pressureBytes); assert(CustodyOwnedMemory::usedBytes() == before); verify(copied);
        }
        const auto invokePacked = [&](std::size_t failAt) {
            migrationAllocation = {true, false, 0, failAt};
            auto result = writeCustodyMigration(copied, context, 2, transaction, CustodyMigrationSubject::package, "Pkg");
            migrationAllocation.active = false; return result;
        };
        auto countedPacked = invokePacked(0); assert(countedPacked.ok());
        const auto packedAllocations = migrationAllocation.calls; assert(packedAllocations > 0);
        countedPacked.value.reset(); assert(CustodyOwnedMemory::usedBytes() == before);
        for (std::size_t ordinal = 1; ordinal <= packedAllocations; ++ordinal) {
            auto failed = invokePacked(ordinal);
            assert(migrationAllocation.hit && !failed.ok() && !failed.value && failed.error == CustodyCodecError::allocationFailed);
            assert(CustodyOwnedMemory::usedBytes() == before);
            auto retry = invokePacked(0); assert(retry.ok()); retry.value.reset(); assert(CustodyOwnedMemory::usedBytes() == before);
        }
        std::printf("MIGRATION_PACKED_WRITER_ALLOCATIONS cuts=%zu reader_allocations=0 retry=1\n", packedAllocations);
    }
    CustodyAllocator<std::uint8_t> allocator; const auto pressureCount=CustodyOwnedMemory::limit-before;
    auto* pressure=allocator.allocate(pressureCount);
    migrationAllocation = {true, false, 0, 0};
    const auto fullQuotaRead = readCustodyMigration(valid,context,2,transaction,CustodyMigrationSubject::queue,"");
    migrationAllocation.active = false;
    assert(fullQuotaRead.ok() && migrationAllocation.calls == 0); // Actual no-heap reader, not skipped cuts.
    const auto refused=writeCustodyMigration(value,context,2,transaction,CustodyMigrationSubject::queue,"");
    assert(!refused.ok() && !refused.value && refused.error==CustodyCodecError::allocationFailed);
    assert(CustodyOwnedMemory::usedBytes()==CustodyOwnedMemory::limit);
    bad=value; bad.stage=static_cast<CustodyMigrationStage>(-1);
    assert(writeCustodyMigration(bad,context,2,transaction,CustodyMigrationSubject::queue,"").error==CustodyCodecError::invalidInput);
    allocator.deallocate(pressure,pressureCount); assert(CustodyOwnedMemory::usedBytes()==before);
    assert(emit(value)==valid); assert(CustodyOwnedMemory::usedBytes()==before);
    const auto invoke = [&](std::size_t failAt) {
        migrationAllocation = {true, false, 0, failAt};
        auto result = writeCustodyMigration(value, context, 2, transaction, CustodyMigrationSubject::queue, "");
        migrationAllocation.active = false;
        return result;
    };
    auto counted = invoke(0); assert(counted.ok()); const auto allocationCount = migrationAllocation.calls; assert(allocationCount > 0);
    counted.value.reset(); assert(CustodyOwnedMemory::usedBytes() == before);
    for (std::size_t ordinal = 1; ordinal <= allocationCount; ++ordinal) {
        auto failed = invoke(ordinal);
        assert(migrationAllocation.hit && !failed.ok() && !failed.value && failed.error == CustodyCodecError::allocationFailed);
        assert(CustodyOwnedMemory::usedBytes() == before);
        auto retry = invoke(0); assert(retry.ok()); retry.value.reset(); assert(CustodyOwnedMemory::usedBytes() == before);
    }
    std::printf("MIGRATION_WRITER_ALLOCATIONS schema=%u cuts=%zu reader_allocations=0 retry=1\n", schema, allocationCount);
    std::printf("MIGRATION_CODEC_MATRIX schema=%u accepted=%zu rejected=%zu cap=65536 allocation_refusal=1 retry=1\n",schema,accepted,rejected);
}
}
int main() {
    const auto initialOwned = CustodyOwnedMemory::usedBytes();
    auto migrationOwn = own; migrationOwn.role = CustodyRole::migrationIntent;
    CustodyId transaction{}; transaction.fill(0x44);
    const std::string migrationV2 = "{\"schema\":\"graf.custody.migration.v2\",\"store_id\":\"" + std::string(32,'1') +
        "\",\"object_id\":\"" + std::string(32,'2') + "\",\"generation\":1,\"transaction_id\":\"" + std::string(32,'4') +
        "\",\"subject\":\"queue\",\"directory_id\":null,\"stage\":\"prepared\",\"ledger_anchor\":{\"object_id\":null,\"generation\":null,\"length\":3,\"sha256\":\"" +
        std::string(64,'6') + "\"},\"sources\":[{\"source\":\"ledger\",\"source_length\":3,\"source_sha256\":\"" + std::string(64,'6') +
        "\",\"destination_object_id\":\"" + std::string(32,'5') + "\",\"destination_generation\":null,\"destination_length\":null,\"destination_sha256\":null,"
        "\"destination_representation\":\"flat_v1\",\"destination_container_id\":null,\"destination_committed_extent\":null,\"destination_root_ref\":null}],\"barrier\":null,\"cleanup_authorization\":null}";
    assert(readCustodyMigration(migrationV2, migrationOwn, 1, transaction, CustodyMigrationSubject::queue, "").ok());
    const std::string migration = "{\"schema\":\"graf.custody.migration.v1\",\"store_id\":\"" + std::string(32,'1') +
        "\",\"object_id\":\"" + std::string(32,'2') + "\",\"generation\":1,\"transaction_id\":\"" + std::string(32,'4') +
        "\",\"subject\":\"queue\",\"directory_id\":null,\"stage\":\"prepared\",\"ledger_anchor\":{\"object_id\":null,\"generation\":null,\"length\":3,\"sha256\":\"" +
        std::string(64,'6') + "\"},\"sources\":[{\"source\":\"ledger\",\"source_length\":3,\"source_sha256\":\"" + std::string(64,'6') +
        "\",\"destination_object_id\":\"" + std::string(32,'5') + "\",\"destination_generation\":null,\"destination_length\":null,\"destination_sha256\":null}],\"barrier\":null,\"cleanup_authorization\":null}";
    const auto migrationDecoded = readCustodyMigration(migration, migrationOwn, 1, transaction, CustodyMigrationSubject::queue, "");
    assert(migrationDecoded.ok());
    migrationTests(migration, migrationOwn, transaction);
    migrationTests(migrationV2, migrationOwn, transaction, 2);
    auto bootstrapOwn = own; bootstrapOwn.role = CustodyRole::bootstrap;
    CustodyId queueId{}; queueId.fill(0x33);
    const std::string bootstrap = "{\"schema\":\"graf.custody.bootstrap.v1\",\"store_id\":\"" + std::string(32, '1') +
        "\",\"object_id\":\"" + std::string(32, '2') + "\",\"generation\":5,\"mode\":\"protected\",\"queue_object_id\":\"" +
        std::string(32, '3') + "\",\"transaction_id\":null,\"subject\":null,\"directory_id\":null}";
    const auto bootstrapDecoded = readCustodyBootstrap(bootstrap, bootstrapOwn, 5, queueId);
    assert(bootstrapDecoded.ok());
    bootstrapTests(bootstrapOwn, queueId);
    for (bool v2 : {false, true}) {
        const auto valid = package(v2, ref(v2));
        const auto decoded = read(valid); assert(decoded.ok());
        assert(decoded.value->generation == 5 && decoded.value->refCount == 1);
        const auto output = serialized(*decoded.value); assert(output == valid);
        assert(serialized(*read(output).value) == output);
        assert(read(replace(valid, "\"schema\"", "\"sch\\u0065ma\"")).ok());
        assert(read(" \r\n\t" + valid + " \n").ok());
        assert(read(replace(valid, "\"generation\":5", "\"generation\": 5")).ok());
        for (const auto bad : {"-1", "01", "1.0", "5e0", "18446744073709551616", "null", "true"})
            reject(replace(valid, "\"generation\":5", std::string("\"generation\":") + bad));
        for (const auto bad : {"schema_version", "SCHEMA", "unknown"}) reject(replace(valid, "\"schema\"", std::string("\"") + bad + "\""));
        reject(replace(valid, "\"generation\":5", "\"generation\":5,\"gener\\u0061tion\":5"));
        reject(replace(valid, "\"binding\":\"live\"", "\"binding\":\"live\",\"binding\":\"live\""));
        reject(replace(valid, "\"refs\":[", "\"extra\":null,\"refs\":["));
        reject(replace(valid, "\"reason\":\"\",", ""));
        reject(replace(valid, "\"directory_id\":\"test-package\"", "\"directory_id\":\"test/package\""));
        reject(replace(valid, "\"phase\":\"capturing\"", "\"phase\":\"unknown\""));
        reject(replace(valid, "\"reason\":\"\"", "\"reason\":\"none\""));
        reject(replace(valid, "\"short_recording_discarded\":false", "\"short_recording_discarded\":0"));
        reject(replace(valid, "\"generation\":null", "\"generation\":1"));
        reject(package(v2, ref(v2) + "," + ref(v2)));
        reject(package(v2, ""));
        reject(valid + "x"); reject("\xef\xbb\xbf" + valid);
        reject(replace(valid, "test-package", "test-\\ud800"));
        reject(replace(valid, "test-package", std::string("test-") + '\xff'));
        reject(replace(valid, "test-package", "test-\\u00e9"));
        reject(replace(valid, "test-package", "test-\\q"));
        reject(replace(valid, "\"refs\":[", "\"refs\":[[[[["));
        reject(replace(valid, "\"refs\":[", "\"refs\":[,"));
        assert(!readCustodyPackage(valid, own, 6, "test-package").ok());
        assert(!readCustodyPackage(valid, own, 5, "other").ok());
        auto other = own; other.storeId[0] ^= 1;
        assert(!readCustodyPackage(valid, other, 5, "test-package").ok());
        other = own; other.role = CustodyRole::manifest;
        assert(!readCustodyPackage(valid, other, 5, "test-package").ok());
        auto padded = valid; padded.append(65536 - padded.size(), ' '); assert(read(padded).ok());
        padded += ' '; reject(padded);
        const auto sealed = package(v2, ref(v2, false, "media") + "," + ref(v2, false, "playback") + "," + ref(v2, false, "manifest"), "sealed_normal");
        assert(read(sealed).ok()); assert(read(serialized(*read(sealed).value)).ok());
        reject(replace(sealed, "\"length\":96", "\"length\":null"));
        reject(replace(sealed, "\"length\":96", "\"length\":68719476737"));
        reject(replace(sealed, "\"generation\":7", "\"generation\":0"));
        reject(package(v2, ref(v2, false, "media"), "sealed_normal"));
        assert(read(package(v2, "", "sealed_degraded", "clock_discontinuity")).ok());
        reject(package(v2, "", "sealed_degraded"));
        reject(package(v2, "", "sealed_degraded", "unknown_reason"));
        auto mutated = *decoded.value; mutated.schema = 3;
        assert(!writeCustodyPackage(mutated, own, 5, "test-package").ok());
        mutated = *decoded.value; mutated.refs[0].generation = 1;
        assert(!writeCustodyPackage(mutated, own, 5, "test-package").ok());
        const auto schemaEnd = valid.find(',');
        assert(read(valid.substr(schemaEnd+1, valid.size()-schemaEnd-2) + "," + valid.substr(1, schemaEnd-1) + "}").ok() == false); // Missing opening brace.
        assert(read("{" + valid.substr(schemaEnd+1, valid.size()-schemaEnd-2) + "," + valid.substr(1, schemaEnd-1) + "}").ok());
        reject(package(v2, ref(v2) + "," + ref(v2, false, "media") + "," + ref(v2, false, "playback") + "," + ref(v2, false, "manifest") + "," + ref(v2, false, "recovery") + "," + ref(v2)));
        const std::string maxName(300, 'a');
        const auto maxDirectory = replace(valid, "test-package", maxName);
        const auto maxDecoded = readCustodyPackage(maxDirectory, own, 5, maxName); assert(maxDecoded.ok());
        assert(writeCustodyPackage(*maxDecoded.value, own, 5, maxName).ok());
        reject(replace(valid, "test-package", std::string(301, 'a')));
        const auto owned = CustodyOwnedMemory::usedBytes();
        CustodyAllocator<std::uint8_t> allocator;
        const auto pressureCount = CustodyOwnedMemory::limit - owned;
        auto* pressure = allocator.allocate(pressureCount);
        assert(read(valid).ok()); // Fixed-shape reader does not allocate, even at the full shared budget.
        const auto refused = writeCustodyPackage(*decoded.value, own, 5, "test-package");
        assert(!refused.ok() && refused.error == CustodyCodecError::allocationFailed);
        assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
        allocator.deallocate(pressure, pressureCount);
        assert(CustodyOwnedMemory::usedBytes() == owned);
    }
    const auto flat = package(true, ref(true));
    auto packed = replace(flat, "\"representation\":\"flat_v1\"", "\"representation\":\"packed_v2\"");
    reject(packed); // A packed live object must already have its reserved container ID.
    packed = replace(packed, "\"container_id\":null", "\"container_id\":\"" + std::string(32, '5') + "\"");
    assert(read(packed).ok()); assert(serialized(*read(packed).value) == packed);
    reject(replace(packed, "\"committed_extent\":null", "\"committed_extent\":32896"));
    reject(replace(packed, "\"role\":\"canonical\"", "\"role\":\"manifest\""));
    reject(replace(packed, "graf.custody.package.v2", "graf.custody.package.v1"));
    reject(replace(packed, "packed_v2", "unknown"));
    PackedReference root{PackedRecordKind::nodeL2, 128, ProtectedPackedCustodyFormat::appendOffset, 7, 0, {}};
    root.envelopeSha.fill(1);
    const auto rootBytes = ProtectedPackedCustodyFormat::encodeReference(root); assert(rootBytes);
    std::string rootHex;
    for (auto byte : *rootBytes) { rootHex += "0123456789abcdef"[byte >> 4]; rootHex += "0123456789abcdef"[byte & 15]; }
    auto sealedPacked = package(true, ref(true, false), "sealed_degraded", "clock_discontinuity");
    sealedPacked = replace(sealedPacked, "flat_v1", "packed_v2");
    sealedPacked = replace(sealedPacked, "\"container_id\":null", "\"container_id\":\"" + std::string(32, '5') + "\"");
    sealedPacked = replace(sealedPacked, "\"committed_extent\":null", "\"committed_extent\":33024");
    sealedPacked = replace(sealedPacked, "\"root_ref\":null", "\"root_ref\":\"" + rootHex + "\"");
    assert(read(sealedPacked).ok()); assert(serialized(*read(sealedPacked).value) == sealedPacked);
    reject(replace(sealedPacked, "\"committed_extent\":33024", "\"committed_extent\":32896"));
    reject(replace(sealedPacked, "\"root_ref\":\"" + rootHex + "\"", "\"root_ref\":\"" + std::string(128, '0') + "\""));
    reject(replace(sealedPacked, "\"generation\":7", "\"generation\":6"));
    reject(replace(sealedPacked, "\"length\":96", "\"length\":0"));
    auto emptyPacked = replace(sealedPacked, "\"length\":96", "\"length\":0");
    emptyPacked = replace(emptyPacked, "\"generation\":7", "\"generation\":1");
    emptyPacked = replace(emptyPacked, "\"committed_extent\":33024", "\"committed_extent\":32896");
    emptyPacked = replace(emptyPacked, rootHex, std::string(128, '0'));
    assert(read(emptyPacked).ok()); // Structural empty root, NOT a normal recording/trusted prefix proof.
    reject(replace(emptyPacked, "\"length\":0", "\"length\":1"));
    assert(read(package(true, ref(true, false, "manifest"), "discard_pending", "", true)).ok());
    reject(package(true, ref(true, false, "manifest"), "discard_pending"));
    reject(package(true, "", "discard_pending", "", true));
    assert(CustodyOwnedMemory::usedBytes() == initialOwned);
}
