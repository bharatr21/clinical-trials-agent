import { expect, test } from "@playwright/test";

test.describe("Home Page", () => {
  test("should display the header with title", async ({ page }) => {
    await page.goto("/");

    // Check header is visible
    await expect(page.getByRole("heading", { name: "Clinical Trials Agent" })).toBeVisible();
    await expect(page.getByText("Query the AACT database using natural language")).toBeVisible();
  });

  test("should display example questions section", async ({ page }) => {
    await page.goto("/");

    // Check example questions card
    await expect(page.getByText("Try an example question")).toBeVisible();
    await expect(page.getByRole("button", { name: /breast cancer trials/i })).toBeVisible();
  });

  test("should display the chat interface", async ({ page }) => {
    await page.goto("/");

    // Check chat interface elements
    await expect(page.getByText("Start a conversation")).toBeVisible();
    await expect(page.getByPlaceholder("Ask about clinical trials...")).toBeVisible();
    await expect(page.getByRole("button").filter({ has: page.locator("svg") })).toBeVisible();
  });

  test("should display footer with AACT link", async ({ page }) => {
    await page.goto("/");

    // Check footer
    await expect(page.getByText("Powered by")).toBeVisible();
    await expect(page.getByRole("link", { name: "AACT Database" })).toHaveAttribute(
      "href",
      "https://aact.ctti-clinicaltrials.org/",
    );
  });
});

test.describe("Example Questions", () => {
  test("should populate input when clicking an example question", async ({ page }) => {
    await page.goto("/");

    const input = page.getByPlaceholder("Ask about clinical trials...");
    await expect(input).toHaveValue("");

    // Click an example question
    await page.getByRole("button", { name: /breast cancer trials/i }).click();

    // Input should be populated
    await expect(input).toHaveValue(/breast cancer/i);
  });

  test("should show all example questions", async ({ page }) => {
    await page.goto("/");

    const examples = [
      /breast cancer trials/i,
      /Phase 3 diabetes/i,
      /COVID-19 vaccine/i,
      /California/i,
      /common conditions/i,
    ];

    for (const example of examples) {
      await expect(page.getByRole("button", { name: example })).toBeVisible();
    }
  });
});

test.describe("Chat Interface", () => {
  test("should disable submit button when input is empty", async ({ page }) => {
    await page.goto("/");

    const submitButton = page
      .getByRole("button")
      .filter({ has: page.locator('svg[class*="lucide-send"]') });
    await expect(submitButton).toBeDisabled();
  });

  test("should enable submit button when input has text", async ({ page }) => {
    await page.goto("/");

    const input = page.getByPlaceholder("Ask about clinical trials...");
    await input.fill("How many trials exist?");

    // Find the submit button (the one with Send icon)
    const submitButton = page.locator('button[type="submit"]');
    await expect(submitButton).toBeEnabled();
  });

  test("should show user message after submission", async ({ page }) => {
    await page.goto("/");

    const input = page.getByPlaceholder("Ask about clinical trials...");
    await input.fill("Test question");

    // Submit the form
    await page.locator('button[type="submit"]').click();

    // User message should appear
    await expect(page.getByText("Test question")).toBeVisible();

    // Loading state should appear
    await expect(page.getByText("Analyzing your question...")).toBeVisible();
  });

  test("should clear input after submission", async ({ page }) => {
    await page.goto("/");

    const input = page.getByPlaceholder("Ask about clinical trials...");
    await input.fill("Test question");

    await page.locator('button[type="submit"]').click();

    // Input should be cleared
    await expect(input).toHaveValue("");
  });
});

test.describe("Accessibility", () => {
  test("should have proper heading hierarchy", async ({ page }) => {
    await page.goto("/");

    const h1 = page.getByRole("heading", { level: 1 });
    await expect(h1).toHaveCount(1);
    await expect(h1).toHaveText("Clinical Trials Agent");
  });

  test("should have accessible input with placeholder", async ({ page }) => {
    await page.goto("/");

    const input = page.getByPlaceholder("Ask about clinical trials...");
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();
  });

  test("should have proper link attributes for external links", async ({ page }) => {
    await page.goto("/");

    const aactLink = page.getByRole("link", { name: "AACT Database" });
    await expect(aactLink).toHaveAttribute("target", "_blank");
    await expect(aactLink).toHaveAttribute("rel", /noopener/);
  });
});
