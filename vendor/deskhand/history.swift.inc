    func trimmedHistory(_ messages: [ChatMessage]) -> [ChatMessage] {
        var seenImages = 0
        // Apps admitted to the tree cap, newest first.
        var keptApps: [String] = []
        // Apps whose newest tree has already been walked past.
        var sawTree = Set<String>()
        var diffsKept = 0
        var result: [ChatMessage] = []

        for message in messages.reversed() {
            var copy = message

            if !copy.images.isEmpty {
                seenImages += 1
                if seenImages > options.keepScreenshots {
                    copy.images = []
                    if copy.text.isEmpty { continue }
                }
            }

            // What an action changed is only worth its lines until the next
            // action changes something else: a diff describes a transition, and
            // a transition three steps back is history that no longer matches
            // anything on screen. They are also the second-biggest thing in a
            // long run — measured 44 KB of a 169 KB prompt on a 30-step run —
            // and every byte is paid again on every following round trip.
            if copy.role == .tool, copy.text.contains(Self.diffMarkerPrefix) {
                diffsKept += 1
                if diffsKept > 1 {
                    copy.text = Self.compactDiff(in: copy.text)
                }
            }

            if copy.role == .tool, copy.text.contains(Self.treeMarkerPrefix) {
                let app = Self.appKey(forTreeMessage: copy.text)
                // Only the newest tree per app is authoritative: an older one
                // advertises indices that no longer resolve to what the model
                // thinks they do. The cap bounds how many apps keep one.
                let isNewestForApp = sawTree.insert(app).inserted
                if isNewestForApp, keptApps.count < options.keepTrees {
                    keptApps.append(app)
                } else {
                    copy.text = Self.compactTree(in: copy.text)
                }
            }

            result.append(copy)
        }
        return result.reversed()
    }

    /// Which app a `get_app_state` result came from.
    ///
    /// The header is `Name [bundle.id] — window "Title"`, so the bracketed
    /// bundle identifier is the stable key. Falling back to the whole header
    /// keeps unparseable results from all sharing one bucket.
    static func appKey(forTreeMessage text: String) -> String {
        guard let close = text.firstIndex(of: "]"),
            let open = text[text.startIndex..<close].lastIndex(of: "[")
        else {
            return String(text.prefix(40))
        }
        return String(text[text.index(after: open)..<close])
    }

    static let treeMarkerPrefix = "Accessibility tree ("

    /// Where a tool result starts describing what the action changed.
    static let diffMarkerPrefix = "Changed after "

    /// Cuts the "what changed" block out of a result that a later action has
    /// already superseded.
    ///
    /// The tree below it, if any, is left alone: it is either the newest tree of
    /// its app — which the model still needs — or it is compacted by its own
    /// rule a few lines down.
    static func compactDiff(in text: String) -> String {
        guard let start = text.range(of: diffMarkerPrefix) else { return text }
        let tree = text.range(of: treeMarkerPrefix, range: start.lowerBound..<text.endIndex)
        let end = tree?.lowerBound ?? text.endIndex
        return String(text[text.startIndex..<start.lowerBound])
            + "Changed after that: the details are superseded by a later action.\n"
            + String(text[end...])
    }

    /// Cuts the tree section out of a tool result, keeping the cheap header.
    ///
    /// The tree is always the last block of a `get_app_state` result, so
    /// everything from the marker on can go.
    static func compactTree(in text: String) -> String {
        guard let range = text.range(of: treeMarkerPrefix) else { return text }
        let header = text[text.startIndex..<range.lowerBound]
        return header + "Accessibility tree omitted to keep the prompt small. Element numbers "
            + "are stable, so the indices you already used still mean the same controls."
    }

