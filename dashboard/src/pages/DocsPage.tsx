import { StaticPageShell } from '../components/legal/StaticPageShell'

export function DocsPage() {
  return (
    <StaticPageShell
      title="Documentation"
      subtitle="Everything you need to install, configure, and understand PRLens — the AI code reviewer for GitHub pull requests."
      updated="July 10, 2026"
    >
      <h2 id="what-it-does">What PRLens does</h2>
      <p>
        PRLens reviews every pull request the moment it's opened or updated. It reads the diff, sends
        the changed code to an LLM (GPT-4o via Azure OpenAI) for analysis, and posts the results
        straight back to the PR: inline comments on the exact lines with issues, a quality score out
        of 100, a severity breakdown, and a formal review verdict — <strong>Approve</strong>,{' '}
        <strong>Request changes</strong>, or <strong>Comment</strong>.
      </p>
      <p>
        It looks for four categories of problems in the changed code:
      </p>
      <ul>
        <li>
          <strong>Security</strong> — OWASP Top 10 issues, SQL injection, hardcoded secrets, path
          traversal, command injection, XSS, unsafe deserialization, and authentication flaws.
        </li>
        <li>
          <strong>Quality</strong> — excessive nesting, duplicated logic, "god functions", bare{' '}
          <code>except</code> blocks, and poor error handling.
        </li>
        <li>
          <strong>Performance</strong> — N+1 query patterns, expensive work inside loops, blocking
          calls on hot paths, and inefficient algorithms.
        </li>
        <li>
          <strong>Style &amp; documentation</strong> — confusing naming, missing input validation, and
          documentation gaps that create real maintainability risk.
        </li>
      </ul>
      <p>
        PRLens only reviews lines that appear in the diff — pre-existing issues in code you didn't
        touch are out of scope by design, so reviews stay focused on what changed.
      </p>

      <h2 id="installation">Installing PRLens (GitHub App)</h2>
      <p>
        The dashboard installs PRLens as a GitHub App, which is the recommended path for most teams
        and requires no server or workflow file of your own.
      </p>
      <ol>
        <li>Sign in to the dashboard with your GitHub account.</li>
        <li>
          From <strong>Connect a repository</strong>, choose the organization or account that owns
          the repository you want reviewed.
        </li>
        <li>
          Grant the app access to that repository (or to all repositories, if you'd rather manage
          access from GitHub's App settings later).
        </li>
        <li>
          Select the repository in the dashboard and toggle it <strong>active</strong>. PRLens starts
          reviewing new and updated pull requests immediately — nothing to add to the repo itself.
        </li>
      </ol>
      <p>
        Once installed, the app authenticates as itself (short-lived, auto-refreshed installation
        tokens) rather than as a personal account, so reviews aren't tied to any one person's GitHub
        access.
      </p>

      <h2 id="configuration">Configuration options</h2>
      <p>
        Every connected repository has its own review configuration, editable from that repository's
        settings page in the dashboard. Changes apply to all new pull requests — in-flight reviews
        aren't retroactively re-scored.
      </p>
      <table>
        <thead>
          <tr>
            <th>Field</th>
            <th>Type</th>
            <th>Default</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>Minimum severity</code></td>
            <td>info / warning / error / critical</td>
            <td>info</td>
            <td>Comments below this severity are dropped before they're posted to the PR.</td>
          </tr>
          <tr>
            <td><code>Target languages</code></td>
            <td>toggle list</td>
            <td>all</td>
            <td>
              Restricts review to specific languages. Currently supported: Python, JavaScript,
              TypeScript, and Java. Leave everything enabled to review all supported languages.
            </td>
          </tr>
          <tr>
            <td><code>Approve threshold</code></td>
            <td>0–100</td>
            <td>80</td>
            <td>
              A score strictly above this value, with no critical issues, results in an{' '}
              <strong>Approve</strong> verdict.
            </td>
          </tr>
          <tr>
            <td><code>Request-changes threshold</code></td>
            <td>0–100</td>
            <td>50</td>
            <td>
              A score below this value — or any critical issue, regardless of score — results in a{' '}
              <strong>Request changes</strong> verdict. Scores between the two thresholds get a{' '}
              <strong>Comment</strong> verdict.
            </td>
          </tr>
          <tr>
            <td><code>Excluded files</code></td>
            <td>glob patterns</td>
            <td>none</td>
            <td>
              Files matching any pattern (e.g. <code>*.lock</code>, <code>dist/**</code>) are skipped
              entirely, even if they appear in the diff.
            </td>
          </tr>
          <tr>
            <td><code>Reviewer mapping</code></td>
            <td>issue type → reviewer</td>
            <td>none</td>
            <td>
              Maps an issue category (security, performance, quality, style, documentation) to a
              GitHub username or team. When a PR has a critical issue in that category, PRLens
              requests that reviewer automatically. The mapped account must be a collaborator on the
              repository, or GitHub will reject the request — PRLens logs a warning and continues
              rather than failing the review.
            </td>
          </tr>
        </tbody>
      </table>
      <p>
        Teams running PRLens outside the dashboard (self-hosted GitHub Actions or webhook mode) can
        set the same options via a <code>.aireviewer.yml</code> file at the repository root, plus a
        few engineering-level fields not exposed in the UI: <code>llm_model</code>,{' '}
        <code>max_workers</code>, and <code>large_pr_threshold</code> (the file-count above which a
        PR gets the <code>large-pr</code> label).
      </p>

      <h2 id="scoring">The quality score and severity levels</h2>
      <p>
        Every review produces a score from 0 to 100, starting at 100 and reduced by a fixed penalty
        for each issue found, weighted by severity:
      </p>
      <table>
        <thead>
          <tr>
            <th>Severity</th>
            <th>Penalty</th>
            <th>Meaning</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><span className="prl-mono">🔴 critical</span></td>
            <td>−25</td>
            <td>Likely to cause a security breach, data loss, or a production outage.</td>
          </tr>
          <tr>
            <td><span className="prl-mono">🟠 error</span></td>
            <td>−10</td>
            <td>A real bug or defect that will misbehave in some code paths.</td>
          </tr>
          <tr>
            <td><span className="prl-mono">🟡 warning</span></td>
            <td>−4</td>
            <td>A quality, performance, or maintainability concern worth addressing.</td>
          </tr>
          <tr>
            <td><span className="prl-mono">🔵 info</span></td>
            <td>−1</td>
            <td>A minor style or documentation note.</td>
          </tr>
        </tbody>
      </table>
      <p>
        The score and issue severities determine the verdict: any critical issue, or a score below
        the request-changes threshold, produces <strong>Request changes</strong>; a score above the
        approve threshold with no critical issues produces <strong>Approve</strong>; anything in
        between produces <strong>Comment</strong>. If some files can't be analyzed, the review is
        marked <strong>Incomplete</strong> instead of silently under-reporting issues; if analysis
        fails entirely, it's marked <strong>Total failure</strong> so you know not to trust the
        result.
      </p>

      <h2 id="inline-comments">How inline comments work</h2>
      <p>
        PRLens posts two kinds of feedback on each pull request:
      </p>
      <ul>
        <li>
          <strong>A summary comment</strong>, posted once, containing the overall verdict, the score,
          a breakdown of issues by severity, positive observations about the change, and top-level
          recommendations.
        </li>
        <li>
          <strong>Inline comments</strong>, attached to the exact diff line where an issue was found,
          each prefixed with a severity emoji and, where applicable, a concrete code suggestion for
          how to fix it.
        </li>
      </ul>
      <p>
        A typical inline comment looks like this:
      </p>
      <pre>
        <code>{`🔴 Hardcoded API key committed to source. Anyone with repo access can read
this secret, and it will remain in git history even if removed later.

💡 Suggestion: Load the key from an environment variable, e.g.
API_KEY = os.environ["OPENAI_API_KEY"]`}</code>
      </pre>
      <p>
        PRLens also applies labels automatically (e.g. <code>needs-changes</code>,{' '}
        <code>security-concern</code>, <code>large-pr</code>), and submits a formal GitHub review
        with the computed verdict so the PR's review status reflects the result — not just a comment
        buried in the thread.
      </p>

      <h2 id="deployment-modes">The two deployment modes</h2>
      <p>
        Under the hood, both modes run the same review pipeline — they only differ in how a PR event
        reaches PRLens.
      </p>
      <h3>GitHub Actions mode</h3>
      <p>
        PRLens runs as a step inside your own GitHub Actions workflow, once per pull request event.
        There's no server to host: you add a workflow file to the repository and supply your Azure
        OpenAI credentials as repository secrets. Comments are posted by <code>github-actions[bot]</code>.
        This mode is a good fit for teams that want the review logic to live entirely inside their CI
        configuration, or that can't install a GitHub App on their organization.
      </p>
      <h3>Webhook mode (used by this dashboard)</h3>
      <p>
        PRLens runs as a long-lived server that receives pull request events directly from GitHub via
        a registered GitHub App webhook. Installing the app takes zero per-repository setup — every
        repo the app is installed on gets reviews automatically. The webhook verifies each incoming
        request's signature (HMAC-SHA256) before processing it, and only acts on{' '}
        <code>opened</code>, <code>synchronize</code>, and <code>reopened</code> events. This is the
        mode powering the hosted dashboard, and is the simplest option if you'd rather not manage
        workflow files across many repositories.
      </p>
    </StaticPageShell>
  )
}
