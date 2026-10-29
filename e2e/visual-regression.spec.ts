import { test, expect } from '@playwright/test';

/**
 * Headless Horseman Harness (HHH) — Layer 4: Visual Regression & Layout Stability Pattern
 * 
 * Weryfikuje odporność wizualną i brak kolizji layoutu na dwóch kluczowych viewportach:
 * 1. Desktop: 1440x900 (pełna szerokość)
 * 2. Laptop: 1024x768 (ekran 13-14 cali — zapobiega ściskaniu elementów przez boczne panele)
 */

const VIEWPORTS = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'laptop-1024', width: 1024, height: 768 },
];

test.describe('HHH: Visual Regression & Layout Stability Suite', () => {
  for (const vp of VIEWPORTS) {
    test.describe(`Viewport: ${vp.name} (${vp.width}x${vp.height})`, () => {
      test.use({
        viewport: { width: vp.width, height: vp.height },
      });

      test('Layout: strona główna renderuje się bez horyzontalnego scrolla', async ({ page }) => {
        await page.goto(process.env.APP_URL || 'http://localhost:3000/');
        await page.waitForLoadState('domcontentloaded');

        // Wyłącz animacje dla powtarzalności i determinizmu
        await page.addStyleTag({
          content: `
            *, *::before, *::after {
              animation: none !important;
              transition: none !important;
            }
          `,
        });

        // Weryfikacja braku overflow horyzontalnego
        const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
        expect(scrollWidth).toBeLessThanOrEqual(vp.width + 5);

        // Porównanie snapshotu wizualnego
        await expect(page).toHaveScreenshot(`home-${vp.name}.png`, {
          maxDiffPixelRatio: 0.02,
        });
      });
    });
  }
});
