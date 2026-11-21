import Foundation

@main
struct LockRulesTests {
    static func main() throws {
        let fifty = (1...50).map { "site\($0).example.com" }
        try LockRules.checkDomainUnion([fifty])
        try LockRules.checkDomainUnion([fifty, fifty])
        do {
            try LockRules.checkDomainUnion([fifty, ["extra.example.com"]])
            fatalError("An effective union above Apple's 50-domain limit must fail")
        } catch LockFailure.platform { }
        let emoji = String(repeating: "\u{1f600}", count: 128)
        let identifier = try LockRules.identifier(emoji)
        precondition(identifier == emoji)
        do {
            _ = try LockRules.identifier(emoji + "x")
            fatalError("Saved identifiers must remain addressable through 128-code-point routes")
        } catch LockFailure.invalid { }
        let hostname = try LockRules.domain(" EXAMPLE.com. ")
        precondition(hostname == "example.com")
        for invalid in [".example.com", "https://example.com", "*.example.com", "example.com/path", "example.com:443", "a..example.com"] {
            do { _ = try LockRules.domain(invalid); fatalError("Invalid domain was accepted") }
            catch LockFailure.invalid { }
        }
        print("App Lock input boundaries passed")
    }
}
