/** One lightweight still bridges model loading; never retains a second WebGL scene. */
export function createAvatarTransition(host: HTMLElement) {
  let still: HTMLDivElement | undefined;
  let animation: Animation | undefined;
  let generation = 0;
  const clear = () => {
    generation++;
    animation?.cancel();
    animation = undefined;
    still?.remove();
    still = undefined;
  };
  return {
    capture(canvas: HTMLCanvasElement, background: { image?: string; color?: string }) {
      // A redraw immediately before this call avoids preserveDrawingBuffer's per-frame cost.
      const copy = document.createElement('canvas');
      copy.width = canvas.width;
      copy.height = canvas.height;
      const context = copy.getContext('2d');
      if (!context) return;
      try {
        context.drawImage(canvas, 0, 0);
      } catch {
        return; // Capture is cosmetic; it must never prevent model cleanup.
      }
      clear();
      copy.style.cssText = 'width:100%;height:100%;display:block';
      still = document.createElement('div');
      still.setAttribute('aria-hidden', 'true');
      still.dataset.avatarTransition = 'waiting';
      still.style.cssText =
        'position:absolute;inset:0;z-index:1;pointer-events:none;background-size:cover;background-position:center';
      still.style.backgroundImage = background.image ?? '';
      still.style.backgroundColor = background.color ?? '';
      still.appendChild(copy);
      host.appendChild(still);
    },
    waiting() {
      // A third character can arrive before the second finishes loading/fading.
      generation++;
      animation?.cancel();
      animation = undefined;
      if (still) still.dataset.avatarTransition = 'waiting';
    },
    reveal(reducedMotion: boolean) {
      if (!still) return;
      if (reducedMotion || typeof still.animate !== 'function') {
        clear();
        return;
      }
      const current = ++generation;
      still.dataset.avatarTransition = 'fading';
      animation = still.animate([{ opacity: 1 }, { opacity: 0 }], {
        duration: 240,
        easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
        fill: 'forwards',
      });
      void animation.finished.then(
        () => {
          if (current === generation) clear();
        },
        () => {} // Cancellation is expected on rapid handoff or unmount.
      );
    },
    dispose: clear,
  };
}
