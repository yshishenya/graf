public enum AuditEventName: String, Codable, Sendable {
    case driverInstalled = "driver.installed"
    case driverUpdated = "driver.updated"
    case driverRepaired = "driver.repaired"
    case driverUninstalled = "driver.uninstalled"
    case permissionChanged = "permission.changed"
    case routeVerified = "route.verified"
    case captureStarted = "capture.started"
    case captureStopped = "capture.stopped"
    case assistedAutoStartReadinessRecorded = "assisted_auto_start.readiness_recorded"
    case localBufferEntered = "local_buffer.entered"
    case uploadFailed = "upload.failed"
    case localPurgeAcknowledged = "local_purge.acknowledged"
}
