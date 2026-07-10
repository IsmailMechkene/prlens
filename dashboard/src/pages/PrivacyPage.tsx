import { StaticPageShell } from '../components/legal/StaticPageShell'

export function PrivacyPage() {
  return (
    <StaticPageShell
      title="Privacy Policy"
      subtitle="How PRLens collects, uses, and protects your data."
      updated="July 10, 2026"
    >
      <p>
        This Privacy Policy explains how PRLens ("PRLens", "we", "us", or "our") collects,
        uses, stores, and shares information when you use PRLens (the "Service"), an AI-powered code
        review tool for GitHub pull requests. It applies to the PRLens dashboard, the underlying
        webhook service, and the PRLens GitHub App.
      </p>
      <p>
        We are the data controller for the personal data described in this policy. If you are located
        in the European Economic Area (EEA), the United Kingdom, or Switzerland, this policy is
        written to meet our obligations under the General Data Protection Regulation (GDPR).
      </p>

      <h2 id="data-we-collect">1. Data we collect</h2>
      <p>We collect the following categories of data, only as needed to operate the Service:</p>
      <ul>
        <li>
          <strong>GitHub account and profile data.</strong> When you sign in with GitHub OAuth, we
          receive your GitHub username, display name, avatar URL, and the account identifiers needed
          to maintain your session. We do not receive or store your GitHub password.
        </li>
        <li>
          <strong>Repository metadata.</strong> Names, owners, and visibility (public/private) of the
          repositories you connect to PRLens, and the review configuration you set for each one.
        </li>
        <li>
          <strong>Pull request diffs.</strong> When a pull request is opened or updated on a connected
          repository, we retrieve the changed code (the diff) via the GitHub API so it can be
          analyzed. We do not access files outside the diff, and we do not clone or store your
          repository's full source tree.
        </li>
        <li>
          <strong>Review results.</strong> The output PRLens generates for each pull request —
          quality score, severity breakdown, inline comments, and verdict — is stored so it can be
          shown in the dashboard's history and trend views.
        </li>
        <li>
          <strong>Technical and usage data.</strong> Basic operational logs (timestamps, request
          status, error traces) used for debugging and reliability, retained for a limited period as
          described below.
        </li>
      </ul>
      <p>
        We do not collect payment information, government-issued IDs, or any special category of
        personal data under GDPR Article 9.
      </p>

      <h2 id="how-we-use-data">2. How we use your data</h2>
      <p>We use the data described above only for the following purposes:</p>
      <ul>
        <li>To authenticate you and maintain your dashboard session.</li>
        <li>To generate AI-powered code reviews on the pull requests of repositories you've connected.</li>
        <li>To display review history, scores, and repository settings back to you in the dashboard.</li>
        <li>To operate, secure, monitor, and improve the Service, including diagnosing failures.</li>
        <li>To communicate with you about the Service, such as service-related notices, if you contact us or if we need to reach you about your account.</li>
      </ul>
      <p>
        Our legal basis for this processing is the performance of a contract (providing the Service
        you've requested by connecting a repository) and our legitimate interest in operating and
        securing the Service. Where required, we rely on your consent, which you may withdraw at any
        time by disconnecting a repository or deleting your account.
      </p>

      <h2 id="storage">3. Where your data is stored</h2>
      <p>
        Dashboard data — accounts, repository settings, and review results — is stored in a{' '}
        <strong>Supabase-hosted PostgreSQL database</strong>. The application backend runs on{' '}
        <strong>Railway</strong>. Both providers maintain their own security and infrastructure
        safeguards; we configure access controls (authenticated connections, scoped API keys) on top
        of those platforms and do not expose the database directly to the internet.
      </p>
      <p>
        Pull request diffs are sent to <strong>Azure OpenAI</strong> for analysis at review time. Azure
        OpenAI processes this content to generate the review and does not use it to train its
        underlying models; diffs are not retained by Azure OpenAI beyond the processing needed to
        return a result. See{' '}
        <a href="https://learn.microsoft.com/en-us/legal/cognitive-services/openai/data-privacy" target="_blank" rel="noreferrer noopener">
          Microsoft's Azure OpenAI data, privacy, and security documentation
        </a>{' '}
        for details on how Microsoft handles this processing.
      </p>

      <h2 id="retention">4. Data retention</h2>
      <ul>
        <li>
          <strong>Account and profile data</strong> is retained for as long as your account is active,
          and deleted within 30 days of account deletion.
        </li>
        <li>
          <strong>Repository connections and settings</strong> are retained until you disconnect the
          repository or delete your account, at which point they are removed.
        </li>
        <li>
          <strong>Review results</strong> (scores, comments, verdicts) are retained for up to 12
          months to power the dashboard's trend and history views, after which older records are
          purged on a rolling basis.
        </li>
        <li>
          <strong>Pull request diffs</strong> are processed transiently and are not stored beyond the
          time needed to generate a review; only the resulting review output (not the raw diff) is
          persisted.
        </li>
        <li>
          <strong>Operational logs</strong> are retained for up to 90 days for debugging and security
          purposes, then automatically deleted.
        </li>
      </ul>

      <h2 id="sharing">5. Data sharing and third-party processors</h2>
      <p>
        <strong>We do not sell your data.</strong> We do not share your data with third parties for
        their own marketing purposes. We share data only with the service providers (sub-processors)
        needed to operate PRLens, each bound by their own data protection terms:
      </p>
      <table>
        <thead>
          <tr>
            <th>Processor</th>
            <th>Purpose</th>
            <th>Data involved</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>GitHub, Inc.</td>
            <td>OAuth sign-in, reading PR diffs, posting review comments</td>
            <td>Account profile, repository and PR content</td>
          </tr>
          <tr>
            <td>Microsoft Azure OpenAI</td>
            <td>AI analysis of pull request diffs</td>
            <td>Diff content, processed transiently</td>
          </tr>
          <tr>
            <td>Supabase</td>
            <td>Primary application database</td>
            <td>Accounts, repository settings, review results</td>
          </tr>
          <tr>
            <td>Railway</td>
            <td>Application hosting</td>
            <td>All data in transit through the backend service</td>
          </tr>
        </tbody>
      </table>
      <p>
        We may also disclose data if required to do so by law, or to protect the rights, property, or
        safety of PRLens, our users, or others.
      </p>

      <h2 id="security">6. Security</h2>
      <p>
        We use industry-standard measures to protect your data, including encrypted connections
        (TLS) for all data in transit, scoped and rotated credentials for third-party services, and
        HMAC signature verification on all inbound GitHub webhook events. No method of transmission
        or storage is completely secure, and we cannot guarantee absolute security.
      </p>

      <h2 id="your-rights">7. Your rights under GDPR</h2>
      <p>
        If you are located in the EEA, UK, or Switzerland, you have the right to:
      </p>
      <ul>
        <li><strong>Access</strong> the personal data we hold about you.</li>
        <li><strong>Rectify</strong> inaccurate or incomplete data.</li>
        <li><strong>Erase</strong> your data ("right to be forgotten"), including by deleting your account.</li>
        <li><strong>Restrict or object to</strong> certain processing of your data.</li>
        <li><strong>Port</strong> your data to another service in a structured, machine-readable format.</li>
        <li><strong>Withdraw consent</strong> at any time, where processing is based on consent.</li>
        <li><strong>Lodge a complaint</strong> with your local data protection supervisory authority.</li>
      </ul>
      <p>
        You can exercise most of these rights directly from the dashboard (disconnecting
        repositories, deleting your account) or by contacting us using the details below. We will
        respond to verified requests within 30 days.
      </p>

      <h2 id="cookies">8. Cookies and session data</h2>
      <p>
        PRLens uses a single essential session cookie to keep you signed in after GitHub OAuth
        authentication. We do not use advertising or cross-site tracking cookies.
      </p>

      <h2 id="children">9. Children's privacy</h2>
      <p>
        PRLens is not directed at children under 16, and we do not knowingly collect personal data
        from them. If you believe a child has provided us with personal data, contact us and we will
        delete it.
      </p>

      <h2 id="changes">10. Changes to this policy</h2>
      <p>
        We may update this Privacy Policy from time to time. If we make material changes, we will
        update the "Last updated" date above and, where appropriate, notify you through the
        dashboard. Continued use of PRLens after a change takes effect constitutes acceptance of the
        updated policy.
      </p>

      <h2 id="contact">11. Contact us</h2>
      <p>
        If you have questions about this Privacy Policy or want to exercise any of the rights above,
        contact us at{' '}
        <a href="mailto:privacy@prlens.dev">privacy@prlens.dev</a>.
      </p>
    </StaticPageShell>
  )
}
