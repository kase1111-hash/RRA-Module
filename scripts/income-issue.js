/**
 * Keep a "License income" GitHub issue in sync with on-chain income
 *
 * Called from the License Income workflow (actions/github-script) with the
 * output of monitor-income.js. Keeps one open issue whose body shows the
 * current totals and stores the last reading in a hidden marker. When total
 * revenue goes up it adds a comment, which notifies repository watchers.
 */

const { formatUnits } = require("./monitor-income");

const TITLE = "License income";
const STATE_MARKER = /<!-- income-state: (\{.*?\}) -->/s;

function parseState(body) {
  const match = (body || "").match(STATE_MARKER);
  if (!match) return null;
  try {
    return JSON.parse(match[1]);
  } catch {
    return null;
  }
}

function renderBody(status) {
  const state = {
    totalRevenueWei: status.totalRevenueWei,
    checkedAt: status.checkedAt,
    block: status.block,
  };
  return [
    "Tracks license sales for this repository's Story Protocol IP asset.",
    "Updated daily by the **License Income** workflow; a comment is added whenever revenue increases.",
    "",
    "| | |",
    "|---|---|",
    `| IP asset | [\`${status.ipAssetId}\`](https://explorer.story.foundation/ipa/${status.ipAssetId}) |`,
    `| Total revenue received | **${status.totalRevenue} IP** |`,
    `| Unclaimed in royalty vault | ${status.unclaimed} IP |`,
    `| Current minting fee (terms ${status.licenseTermsId}) | ${status.mintingFee} IP |`,
    `| Last checked | ${status.checkedAt} (block ${status.block}) |`,
    "",
    "Revenue is paid in WIP into the IP asset's royalty vault. Claim it with " +
      "`PRIVATE_KEY=0x... node scripts/claim-royalties.js` (after `npm ci` in `scripts/`).",
    "",
    `<!-- income-state: ${JSON.stringify(state)} -->`,
  ].join("\n");
}

function renderIncomeComment(status, previous) {
  const delta = BigInt(status.totalRevenueWei) - BigInt(previous.totalRevenueWei);
  const fee = BigInt(status.mintingFeeWei);
  const lines = [
    `💰 **New license income: +${formatUnits(delta)} IP** since ${previous.checkedAt}`,
    "",
  ];
  if (fee > 0n) {
    const licenses = delta / fee;
    if (licenses > 0n) {
      lines.push(
        `About ${licenses} license${licenses === 1n ? "" : "s"} at the current ` +
          `${status.mintingFee} IP minting fee (royalties from derivatives also count as revenue).`,
        ""
      );
    }
  }
  lines.push(
    `- Total received: **${status.totalRevenue} IP**`,
    `- Unclaimed in royalty vault: ${status.unclaimed} IP`,
    `- [View IP asset](https://explorer.story.foundation/ipa/${status.ipAssetId})`
  );
  return lines.join("\n");
}

async function updateIncomeIssue({ github, context, status, dryRun = false }) {
  const { owner, repo } = context.repo;
  const openIssues = await github.paginate(github.rest.issues.listForRepo, {
    owner,
    repo,
    state: "open",
    per_page: 100,
  });
  const issue = openIssues.find((i) => i.title === TITLE && !i.pull_request);
  const previous = issue ? parseState(issue.body) : null;
  const body = renderBody(status);

  const increased =
    previous !== null && BigInt(status.totalRevenueWei) > BigInt(previous.totalRevenueWei);
  const comment = increased ? renderIncomeComment(status, previous) : null;

  if (dryRun) {
    return { action: "dry-run", issue: issue ? issue.number : null, comment };
  }

  if (!issue) {
    const created = await github.rest.issues.create({ owner, repo, title: TITLE, body });
    return { action: "created", issue: created.data.number, comment: null };
  }

  await github.rest.issues.update({ owner, repo, issue_number: issue.number, body });
  if (comment) {
    await github.rest.issues.createComment({
      owner,
      repo,
      issue_number: issue.number,
      body: comment,
    });
  }
  return { action: comment ? "new-income" : "unchanged", issue: issue.number, comment };
}

module.exports = updateIncomeIssue;
module.exports.parseState = parseState;
module.exports.renderBody = renderBody;
module.exports.renderIncomeComment = renderIncomeComment;
