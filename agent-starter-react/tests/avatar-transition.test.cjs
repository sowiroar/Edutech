const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function setup() {
  const children = new Set();
  const animations = [];
  let captures = 0;
  const context = {
    exports: {},
    document: {
      createElement: () => ({
        style: {},
        dataset: {},
        setAttribute() {},
        appendChild() {},
        getContext: () => ({
          drawImage() {
            captures++;
          },
        }),
        remove() {
          children.delete(this);
        },
        animate(frames, options) {
          let resolve, reject;
          const finished = new Promise((yes, no) => {
            resolve = yes;
            reject = no;
          });
          const animation = {
            finished,
            resolve,
            options,
            cancel: () => reject(new Error('cancelled')),
          };
          animations.push(animation);
          return animation;
        },
      }),
    },
  };
  vm.runInNewContext(
    ts.transpileModule(fs.readFileSync('components/avatar/avatar-transition.ts', 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    context
  );
  const transition = context.exports.createAvatarTransition({
    appendChild: (node) => children.add(node),
  });
  return { transition, children, animations, captures: () => captures };
}
const frame = { width: 960, height: 540 };
test('keeps one still during loading and removes it only after the new frame fades in', async () => {
  const { transition, children, animations, captures } = setup();
  transition.capture(frame, { image: 'url(background.jpg)' });
  transition.waiting();
  assert.equal(children.size, 1);
  assert.equal(captures(), 1);
  transition.reveal(false);
  assert.equal(animations[0].options.duration, 240);
  assert.equal(children.size, 1);
  animations[0].resolve();
  await Promise.resolve();
  assert.equal(children.size, 0);
});
test('rapid handoffs cancel stale fades without deleting the newer still', async () => {
  const { transition, children, animations } = setup();
  transition.capture(frame, {});
  transition.reveal(false);
  animations[0].resolve();
  transition.waiting();
  transition.capture(frame, {});
  await Promise.resolve();
  assert.equal(children.size, 1);
  transition.dispose();
  assert.equal(children.size, 0);
});
test('reduced motion swaps only when ready, without a fade or leftover resources', () => {
  const { transition, children, animations } = setup();
  transition.capture(frame, {});
  assert.equal(children.size, 1);
  transition.reveal(true);
  assert.equal(children.size, 0);
  assert.equal(animations.length, 0);
  transition.dispose();
  transition.dispose();
});
