import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopCabinetBillingHandoffTests: XCTestCase {
    func testBrowserHandoffURLCarriesOnlyOpaqueState() throws {
        let billingURL = try XCTUnwrap(URL(string: "https://rec.2brain.pro/billing"))
        let handoff = try XCTUnwrap(
            DesktopCabinetBillingHandoff.browserURL(for: billingURL, state: "opaque-state-123456")
        )

        XCTAssertEqual(handoff.path, "/billing/handoff")
        XCTAssertEqual(handoff.query, "state=opaque-state-123456")
        XCTAssertFalse(handoff.absoluteString.contains("X-Auth-Session"))
        XCTAssertFalse(handoff.absoluteString.contains("amount"))
    }

    func testHandoffEndpointStaysOnTheBillingOrigin() throws {
        let billingURL = try XCTUnwrap(
            URL(string: "https://user:secret@rec.2brain.pro/billing/checkout?amount=790")
        )
        let endpoint = try XCTUnwrap(DesktopCabinetBillingHandoff.endpointURL(for: billingURL))

        XCTAssertEqual(endpoint.absoluteString, "https://rec.2brain.pro/api/v1/cabinet/billing/handoff")
        XCTAssertNil(endpoint.query)
        XCTAssertNil(endpoint.user)
        XCTAssertNil(endpoint.password)
    }

    func testBillingRoutesStayInsideTheEmbeddedCabinet() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )

        for path in [
            "/billing",
            "/billing/plans",
            "/billing/usage",
            "/billing/subscription",
            "/billing/subscription/cancel",
            "/billing/subscription/resume",
            "/billing/payment-method",
            "/billing/payment-method/delete",
            "/billing/storage",
            "/billing/checkout",
            "/billing/checkout/preview",
            "/billing/checkout/start",
            "/billing/checkout/return",
            "/billing/checkout/status/INV-2026-0001",
            "/billing/checkout/status/INV-2026-0001/refresh",
            "/billing/checkout/status/INV-2026-0001/continue",
            "/billing/discounts",
            "/billing/discounts/apply",
            "/billing/discounts/remove",
            "/billing/trial/activate",
            "/billing/history",
            "/billing/invoices/INV-2026-0001"
        ] {
            let decision = policy.decision(for: try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)")))
            XCTAssertEqual(decision.decision, .allow, path)
            XCTAssertEqual(decision.route.kind, .billing, path)
            XCTAssertEqual(decision.reason, .allowedBilling, path)
            XCTAssertNil(URL(string: "https://rec.2brain.dev\(path)")?.query)
        }
    }

    func testUnknownBillingActionsStayBlocked() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )

        for path in [
            "/billing/checkout/unknown",
            "/billing/checkout/start/extra",
            "/billing/subscription/delete",
            "/billing/discounts/unknown",
            "/billing/checkout/status/INV-2026-0001/delete",
            "/billing/checkout/status/unsafe%2Fnumber/refresh"
        ] {
            let decision = policy.decision(
                for: try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)"))
            )
            XCTAssertEqual(decision.decision, .blockWithMessage, path)
        }
    }

    func testOfferRouteOpensExternallyWithoutCarryingQueryData() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let source = try XCTUnwrap(
            URL(string: "https://rec.2brain.dev/offer?invoice=INV-2026-0001#payment")
        )

        let decision = policy.decision(for: source)
        XCTAssertEqual(decision.decision, .openExternally)
        XCTAssertEqual(decision.route.kind, .external)
        XCTAssertEqual(decision.reason, .openExternalSafeLink)
        XCTAssertEqual(
            policy.sanitizedExternalURL(for: source)?.absoluteString,
            "https://rec.2brain.dev/offer"
        )
        for path in ["/offer/", "//offer", "/offer//", "/offer/extra"] {
            let variant = try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)"))
            XCTAssertEqual(policy.decision(for: variant).decision, .blockWithMessage, path)
            XCTAssertNil(policy.sanitizedExternalURL(for: variant), path)
        }

        let insecurePolicy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "http://rec.2brain.dev"))
        )
        let insecureOffer = try XCTUnwrap(URL(string: "http://rec.2brain.dev/offer"))
        XCTAssertEqual(insecurePolicy.decision(for: insecureOffer).decision, .blockWithMessage)
        XCTAssertNil(insecurePolicy.sanitizedExternalURL(for: insecureOffer))
    }

    func testReferralMenuRoutesOpenInTheBrowserWithoutCarryingQueryData() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )

        for path in ["/referrals", "/account/referrals"] {
            let url = try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)"))
            let decision = policy.decision(for: url)
            XCTAssertEqual(decision.decision, .openExternally, path)
            XCTAssertEqual(decision.reason, .openBrowserOwnedAccount, path)
            XCTAssertNil(url.query)
        }

        for path in ["/referrals/extra", "/account/referrals/extra", "/referrals/unsafe/path"] {
            let decision = policy.decision(for: try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)")))
            XCTAssertEqual(decision.decision, .blockWithMessage, path)
        }
    }

    func testBillingRouteDoesNotProduceAnExternalHandoffURL() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let source = try XCTUnwrap(URL(string: "https://user:secret@rec.2brain.dev/billing/checkout?amount=790&provider_id=pay_033#payment"))

        XCTAssertNil(policy.sanitizedExternalURL(for: source))
    }

    func testUnsafeRouteCannotBeSanitizedForExternalHandoff() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let source = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033?provider_id=pay_033"))

        XCTAssertNil(policy.sanitizedExternalURL(for: source))
    }

    func testExternalHelpHandoffRejectsHTTP() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let source = try XCTUnwrap(URL(string: "http://help.2brain.dev/billing?amount=790"))

        XCTAssertEqual(policy.decision(for: source).decision, .blockWithMessage)
        XCTAssertNil(policy.sanitizedExternalURL(for: source))
    }

    func testOnlyAllowlistedPaymentProviderHostsMayStartTheConfirmationChain() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let checkout = try XCTUnwrap(URL(string: "https://rec.2brain.dev/billing/checkout"))
        let provider = try XCTUnwrap(URL(string: "https://yookassa.test/checkout/abc"))
        let evil = try XCTUnwrap(URL(string: "https://evil.example/checkout/abc"))
        let chain = DesktopCabinetPaymentNavigation(sessionOrigin: policy.cabinetBaseURL)

        XCTAssertTrue(chain.begin(isBillingCheckoutDocument: true, destination: provider).isActive)
        XCTAssertTrue(
            chain.begin(isBillingCheckoutDocument: true, destination: provider).isActive,
            "A resumed payment from any cabinet billing page must open a chain too"
        )
        XCTAssertFalse(chain.begin(isBillingCheckoutDocument: true, destination: evil).isActive)
        XCTAssertFalse(
            chain.begin(isBillingCheckoutDocument: false, destination: provider).isActive,
            "A page that is not the cabinet checkout must not open a payment chain"
        )
        XCTAssertFalse(
            chain.begin(
                isBillingCheckoutDocument: true,
                destination: try XCTUnwrap(URL(string: "http://yookassa.test/checkout/abc"))
            ).isActive,
            "Insecure provider URLs never open a chain"
        )

        // Outside a chain the sandbox stays exactly as strict as before.
        for path in ["/desktop/meetings", "/billing/checkout"] {
            let allowed = policy.decision(
                for: try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)"))
            )
            XCTAssertEqual(allowed.decision, .allow, path)
        }
        XCTAssertEqual(policy.decision(for: provider).decision, .blockWithMessage)
        XCTAssertEqual(policy.decision(for: evil).decision, .blockWithMessage)
        XCTAssertEqual(policy.decision(for: checkout).decision, .allow)
    }

    func testMultiStepConfirmationChainAllowsEveryBankHopAndEndsOnTheCabinet() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let now = Date()

        // Each step is one main-frame navigation on another host, exactly as the
        // WebKit delegate sees a card payment confirmed by redirect.
        let steps: [(
            url: String,
            handedOverFromBilling: Bool,
            chainActiveAfterLoad: Bool,
            reportKeepsChain: Bool
        )] = [
            ("https://rec.2brain.dev/billing/checkout", false, false, false),
            ("https://yookassa.ru/checkout/abc", true, true, true),
            ("https://3ds.issuer-bank-one.example/acs/challenge", false, true, true),
            ("https://yookassa.ru/checkout/abc/processing", false, true, true),
            ("https://3ds.issuer-bank-two.example/3ds2/auth", false, true, true),
            ("https://rec.2brain.dev/billing/checkout/return", false, true, false)
        ]

        var chain = DesktopCabinetPaymentNavigation(sessionOrigin: policy.cabinetBaseURL)
        for step in steps {
            let url = try XCTUnwrap(URL(string: step.url), step.url)

            chain = chain.begin(
                isBillingCheckoutDocument: step.handedOverFromBilling,
                destination: url,
                now: now
            )
            XCTAssertEqual(chain.isActive, step.chainActiveAfterLoad, "active after \(step.url)")

            // Every hop must load; a blocked bank hop is the launch stopper.
            let decision = policy.decision(
                for: url,
                allowExternalPaymentProvider: chain.externalProviderNavigationAllowed
            )
            XCTAssertEqual(decision.decision, .allow, step.url)

            guard chain.isActive else { continue }
            let report = chain.report(loadedURL: url, now: now.addingTimeInterval(60))
            XCTAssertEqual(
                report == .continueSession,
                step.reportKeepsChain,
                "report for \(step.url)"
            )
            if report == .stopSession { chain = chain.stopped() }
        }

        XCTAssertFalse(chain.isActive, "The chain ends once a cabinet document loads again")
        XCTAssertEqual(
            policy.decision(for: try XCTUnwrap(URL(string: "https://rec.2brain.dev/billing")))
                .route.kind,
            .billing
        )
        // After payment the ordinary sandbox is back.
        for abandoned in steps.map(\.url) where !abandoned.hasPrefix("https://rec.2brain.dev") {
            XCTAssertEqual(
                policy.decision(for: try XCTUnwrap(URL(string: abandoned))).decision,
                .blockWithMessage,
                abandoned
            )
        }
    }

    func testAbandonedConfirmationChainExpiresInsteadOfStayingOpen() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let now = Date()
        let provider = try XCTUnwrap(URL(string: "https://yookassa.ru/checkout/abc"))
        let bank = try XCTUnwrap(URL(string: "https://3ds.issuer-bank.example/acs"))

        let chain = DesktopCabinetPaymentNavigation(sessionOrigin: policy.cabinetBaseURL)
            .begin(isBillingCheckoutDocument: true, destination: provider, now: now)
        XCTAssertTrue(chain.isActive)

        let expired = now.addingTimeInterval(DesktopCabinetPaymentNavigation.defaultTimeLimit + 1)
        XCTAssertEqual(chain.report(loadedURL: provider, now: expired), .stopSession)
        XCTAssertEqual(chain.report(loadedURL: bank, now: expired), .stopSession)
    }
}
#endif
