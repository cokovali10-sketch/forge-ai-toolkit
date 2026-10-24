const core = require('@actions/core');
const execa = require('execa');

async function run() {
  try {
    const root = core.getInput('root') || '.';
    const ci = core.getInput('ci') !== 'false';
    const suppress = core.getInput('suppress') !== 'false';
    const force = core.getInput('force') === 'true';
    const pypiPublish = core.getInput('pypi-publish') === 'true';

    // Run forge init
    const { stdout, stderr } = await execa.python(' -m forge init ', [
      `--root=${root}`,
      `--ci=${ci}`,
      `--suppress=${suppress}`,
      `--force=${force}`,
    ]);

    core.setOutput('status', 'success');
    core.setOutput('created', stdout || 'No output');
    core.setOutput('workflow-path', Path.join(root, '.github', 'workflows', 'forge-ci.yml'));

    if (pypiPublish) {
      core.info('PyPI publish enabled - would need additional configuration');
    }

    core.info(`Forge init completed for ${root}`);
    core.info(`CI workflow: ${core.getOutput('workflow-path')}`);
  } catch (error) {
    core.setOutput('status', 'failure');
    core.error(error.message || 'Unknown error');
  }
}

run();

function Path(p) { return p; }