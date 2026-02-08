#!/usr/bin/env python3
"""Inject auto-test trigger using the global handleFileImport bridge."""

import re

AUTOTEST_BLOCK = '''
<!-- P0.2.2 Auto-test trigger (remove after validation) -->
<script>
(function() {
  var P022_AUTOTEST_ENABLED = true;
  if (!P022_AUTOTEST_ENABLED) return;

  console.log('[P0.2.2-AUTOTEST] Auto-test mode activated');

  function waitForReady(cb, retries) {
    if (typeof XLSX !== 'undefined' && typeof window._globalHandleFileImport === 'function') return cb();
    if (retries <= 0) { console.error('[P0.2.2-AUTOTEST] Dependencies never loaded after 15s'); return; }
    setTimeout(function() { waitForReady(cb, retries - 1); }, 500);
  }

  window.addEventListener('load', function() {
    waitForReady(function() {
      console.log('[P0.2.2-AUTOTEST] Fetching fixture...');
      fetch('/ui/viewer/test-data/p022_fixture.xlsx')
        .then(function(resp) {
          if (!resp.ok) throw new Error('Fetch failed: ' + resp.status);
          return resp.arrayBuffer();
        })
        .then(function(buf) {
          console.log('[P0.2.2-AUTOTEST] Fixture fetched (' + buf.byteLength + ' bytes)');

          var fakeFile = new File([buf], 'p022_fixture.xlsx', {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          });

          console.log('[P0.2.2-AUTOTEST] Calling _globalHandleFileImport...');
          window._globalHandleFileImport(fakeFile);

          setTimeout(function() {
            console.log('[P0.2.2-AUTOTEST] Navigating to triage...');
            if (typeof navigateTo === 'function') navigateTo('triage');

            setTimeout(function() {
              console.log('[P0.2.2-AUTOTEST] Triggering renderAnalystTriage...');
              if (typeof renderAnalystTriage === 'function') renderAnalystTriage();

              setTimeout(function() {
                if (typeof P022_RuntimeValidation !== 'undefined') {
                  var result = P022_RuntimeValidation.run();
                  console.log('[P0.2.2-AUTOTEST] Test complete: ' + result.passed + '/' + result.total + ' passed, ' + result.failed + ' failed');
                  window._p022TestResult = result;
                } else {
                  console.error('[P0.2.2-AUTOTEST] P022_RuntimeValidation not found');
                }
              }, 2000);
            }, 2000);
          }, 5000);
        })
        .catch(function(err) {
          console.error('[P0.2.2-AUTOTEST] Fetch error:', err);
        });
    }, 30);
  });
})();
</script>
'''

with open('ui/viewer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

if '<!-- P0.2.2 Auto-test trigger' in content:
    content = re.sub(
        r'<!-- P0\.2\.2 Auto-test trigger.*?</script>\s*',
        '',
        content,
        flags=re.DOTALL
    )

marker = '<!-- P0.2.2 Runtime Truth Validation'
if marker not in content:
    print('ERROR: Self-test block not found')
    exit(1)

content = content.replace(marker, AUTOTEST_BLOCK + '\n' + marker)

with open('ui/viewer/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Auto-test trigger injected (via global bridge _globalHandleFileImport).')
