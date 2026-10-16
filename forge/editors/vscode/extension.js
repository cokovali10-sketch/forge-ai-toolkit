// FORGE Pipe VS Code extension (scaffold: Node.js needed to verify/package).
// Commands: "FORGE: прогнать конвейер" -> runs `pipe run --json` in the
// workspace root and maps review findings to editor diagnostics.
const vscode = require('vscode');
const { execFile } = require('child_process');

function sev(level) {
  return level === 'confirmed'
    ? vscode.DiagnosticSeverity.Error
    : vscode.DiagnosticSeverity.Warning;
}

function activate(context) {
  const diags = vscode.languages.createDiagnosticCollection('forge-pipe');
  const bar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  bar.text = '$(zap) FORGE';
  bar.command = 'forge-pipe.run';
  bar.show();

  const run = vscode.commands.registerCommand('forge-pipe.run', () => {
    const root = (vscode.workspace.workspaceFolders || [])[0];
    if (!root) { vscode.window.showErrorMessage('FORGE: нет открытой папки'); return; }
    bar.text = '$(sync~spin) FORGE…';
    execFile('python', ['-m', 'forge.cli', 'pipe', 'run', root.uri.fsPath, '--json'],
      { cwd: root.uri.fsPath, maxBuffer: 32 * 1024 * 1024 },
      (err, stdout) => {
        let rep;
        try { rep = JSON.parse(stdout.split('\n').find((l) => l.startsWith('{')) || '{}'); }
        catch (e) { vscode.window.showErrorMessage('FORGE: не прочитал отчёт: ' + e); return; }
        const byFile = new Map();
        for (const s of rep.stages || []) {
          for (const f of ((s.data || {}).findings || [])) {
            if (f.suppressed || !f.file) continue;
            const m = /L(\d+)/.exec(f.detail || '');
            const line = m ? parseInt(m[1], 10) - 1 : 0;
            const uri = vscode.Uri.joinPath(root.uri, f.file);
            const d = new vscode.Diagnostic(
              new vscode.Range(line, 0, line, 200),
              `${f.rule}: ${(f.detail || '').slice(0, 200)}`, sev(f.level));
            d.source = 'forge';
            if (!byFile.has(uri.toString())) byFile.set(uri.toString(), { uri, list: [] });
            byFile.get(uri.toString()).list.push(d);
          }
        }
        diags.clear();
        for (const { uri, list } of byFile.values()) diags.set(uri, list);
        bar.text = rep.status === 'SUCCESS' ? '$(check) FORGE' : '$(error) FORGE';
        vscode.window.showInformationMessage(`FORGE: ${rep.status} за ${rep.duration_ms}мс`);
      });
  });
  context.subscriptions.push(run, diags, bar);
}

function deactivate() {}

module.exports = { activate, deactivate };
