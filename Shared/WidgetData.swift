import Foundation

/// Data shared between the main app and widget via direct file in the widget's sandbox container.
///
/// The main app (non-sandboxed) writes a JSON file into the widget extension's container directory.
/// The widget (sandboxed) reads from its own Application Support, which maps to the same path.
struct WidgetAccountData: Codable {
    let email: String          // pre-obfuscated
    let displayName: String    // pre-obfuscated
    let subscriptionType: String?
    let isActive: Bool
    let sessionUtilization: Double?
    let sessionResetTime: String?
    let weeklyUtilization: Double?
    let weeklyResetTime: String?
    let extraUsageEnabled: Bool?
    let hasError: Bool
    let errorMessage: String?

    // Stable, machine-readable quota metadata for local automation. The
    // human-readable reset strings above remain for the widget UI.
    let usageSampledAt: Date?
    let usageSampledAtISO8601: String?
    let usageAgeSeconds: Int?
    let sessionResetsAt: String?
    let weeklyResetsAt: String?
    let retryNotBefore: Date?
    let retryNotBeforeISO8601: String?
    let credentialOwnership: String?
    let quotaStatus: String?
    let automationEligible: Bool?
    let automationBlockReason: String?

    init(
        email: String,
        displayName: String,
        subscriptionType: String?,
        isActive: Bool,
        sessionUtilization: Double?,
        sessionResetTime: String?,
        weeklyUtilization: Double?,
        weeklyResetTime: String?,
        extraUsageEnabled: Bool?,
        hasError: Bool,
        errorMessage: String?,
        usageSampledAt: Date? = nil,
        usageSampledAtISO8601: String? = nil,
        usageAgeSeconds: Int? = nil,
        sessionResetsAt: String? = nil,
        weeklyResetsAt: String? = nil,
        retryNotBefore: Date? = nil,
        retryNotBeforeISO8601: String? = nil,
        credentialOwnership: String? = nil,
        quotaStatus: String? = nil,
        automationEligible: Bool? = nil,
        automationBlockReason: String? = nil
    ) {
        self.email = email
        self.displayName = displayName
        self.subscriptionType = subscriptionType
        self.isActive = isActive
        self.sessionUtilization = sessionUtilization
        self.sessionResetTime = sessionResetTime
        self.weeklyUtilization = weeklyUtilization
        self.weeklyResetTime = weeklyResetTime
        self.extraUsageEnabled = extraUsageEnabled
        self.hasError = hasError
        self.errorMessage = errorMessage
        self.usageSampledAt = usageSampledAt
        self.usageSampledAtISO8601 = usageSampledAtISO8601
        self.usageAgeSeconds = usageAgeSeconds
        self.sessionResetsAt = sessionResetsAt
        self.weeklyResetsAt = weeklyResetsAt
        self.retryNotBefore = retryNotBefore
        self.retryNotBeforeISO8601 = retryNotBeforeISO8601
        self.credentialOwnership = credentialOwnership
        self.quotaStatus = quotaStatus
        self.automationEligible = automationEligible
        self.automationBlockReason = automationBlockReason
    }
}

struct WidgetData: Codable {
    let accounts: [WidgetAccountData]
    let todayCost: Double
    let conversationTurns: Int
    let activeCodingTime: String
    let linesWritten: Int
    let modelUsage: [String: Int]
    let lastUpdated: Date
    let schemaVersion: Int?
    let generatedAtISO8601: String?

    init(
        accounts: [WidgetAccountData],
        todayCost: Double,
        conversationTurns: Int,
        activeCodingTime: String,
        linesWritten: Int,
        modelUsage: [String: Int],
        lastUpdated: Date,
        schemaVersion: Int? = 2,
        generatedAtISO8601: String? = nil
    ) {
        self.accounts = accounts
        self.todayCost = todayCost
        self.conversationTurns = conversationTurns
        self.activeCodingTime = activeCodingTime
        self.linesWritten = linesWritten
        self.modelUsage = modelUsage
        self.lastUpdated = lastUpdated
        self.schemaVersion = schemaVersion
        self.generatedAtISO8601 = generatedAtISO8601
    }

    // Team-ID-prefixed App Group. macOS Sequoia (15+) prompts for App
    // Management on `group.<bundle-id>` style identifiers; the
    // `<TEAMID>.<bundle-id>` form is auto-authorized for Developer-ID-signed
    // apps without a provisioning profile and avoids the prompt entirely.
    private static let appGroupID = "584KQTRF3B.me.xueshi.ccswitcher"
    private static let fileName = "widget-data.json"

    private static var sharedContainerURL: URL? {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: appGroupID)
    }

    /// Load from the shared App Group container.
    static func load() -> WidgetData? {
        guard let containerURL = sharedContainerURL else { return nil }
        let fileURL = containerURL.appendingPathComponent(fileName)
        guard let data = try? Data(contentsOf: fileURL) else { return nil }
        return try? JSONDecoder().decode(WidgetData.self, from: data)
    }

    /// Save to the shared App Group container.
    func save() {
        guard let containerURL = Self.sharedContainerURL else { return }
        let fileURL = containerURL.appendingPathComponent(Self.fileName)
        if let data = try? JSONEncoder().encode(self) {
            try? data.write(to: fileURL, options: .atomic)
        }
    }
}
