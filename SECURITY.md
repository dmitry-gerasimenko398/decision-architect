# Security and privacy

## Local design

The contest release uses no API key, external backend, network service, executable report script, or third-party Python dependency. Reports are standalone HTML generated from validated saved result JSON. User-controlled text is escaped before rendering.

## Sensitive information

Working sessions can contain personal estimates and context. The entire `sessions/` directory is ignored and excluded from the release manifest. Release examples are sanitized separately.

Do not enter or publish unnecessary names, addresses, account data, health details, private employer information, or other identifying material.

## Reports

Generated HTML contains embedded CSS and inline SVG only. It must not contain external resources, JavaScript, forms, frames, machine-specific paths, or executable user content.

Browser print-to-PDF headers and footers may add a local file path even when the HTML source contains none. Disable those browser options for intentional exports.

## Reporting a problem

Until a public repository exists, report a suspected issue directly to the project owner through the private channel used to share the project. Do not publish sensitive reproduction data.
