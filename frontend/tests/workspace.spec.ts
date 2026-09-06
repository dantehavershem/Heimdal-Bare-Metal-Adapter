import { test, expect } from "@playwright/test";
const media = [
  {
    id: 1,
    name: "ubuntu-server-amd64.iso",
    size_bytes: 3500000000,
    storage_id: 1,
    relative_path: "ubuntu-server-amd64.iso",
    sha256: "a".repeat(64),
    analysis: {
      iso9660: true,
      eltorito: true,
      volume_id: "Ubuntu Server",
      detected: {
        architecture: "x86_64",
        family: "linux",
        linux_layout: "casper",
      },
      recommended_adapter: "linux-kernel-initrd",
      evidence: ["Casper kernel and initrd present"],
      paths: { "/CASPER/VMLINUZ": true },
    },
  },
];
const stores = [
  {
    id: 1,
    name: "Deployment library",
    path: "/storage/iso",
    kind: "mounted",
    role: "media",
    enabled: true,
  },
];
test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = { status: "ok" };
    if (path.endsWith("/media")) data = media;
    else if (path.endsWith("/storage")) data = stores;
    else if (path.endsWith("/jobs"))
      data = [
        {
          id: 42,
          kind: "analyze-iso",
          status: "complete",
          progress: 100,
          log: "Analysis complete",
        },
      ];
    else if (path.endsWith("/status"))
      data = { online: true, total_bytes: 1e12, free_bytes: 5e11 };
    else if (path.endsWith("/media/analyze"))
      data = { job_id: 43, status: "queued" };
    await route.fulfill({ json: data });
  });
});
test("library inspection, honest readiness, navigation and responsive layout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/dashboard.png", fullPage: true });
  await page
    .getByRole("button", { name: "Installer ISOs", exact: true })
    .click();
  await expect(
    page.getByText("ubuntu-server-amd64.iso", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Search media").fill("no-match");
  await expect(page.getByText("No media matches")).toBeVisible();
  await page.getByLabel("Search media").fill("");
  await page.getByRole("button", { name: "Inspect", exact: true }).click();
  await expect(
    page.getByText("Casper kernel and initrd present"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create Heimdal capsule" }),
  ).toBeDisabled();
  await page.screenshot({ path: "test-results/analysis.png", fullPage: true });
  for (const name of [
    "Golden Images",
    "Driver Packs",
    "Jobs",
    "PXE Integration",
    "Storage",
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await expect(
      page.getByRole("heading", { name, exact: true, level: 1 }),
    ).toBeVisible();
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Dashboard", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: /From bootable media/ }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
  expect(errors).toEqual([]);
});
test("existing source submits correct storage path and handles rejected jobs", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Add ISO", exact: true }).click();
  await page.getByLabel("Relative ISO path").fill("ubuntu-server-amd64.iso");
  await page.route("**/media/analyze", (route) =>
    route.fulfill({ status: 404, json: { detail: "Media file not found" } }),
  );
  await page.getByRole("button", { name: "Analyze ISO", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Media file not found");
  await expect(
    page.getByRole("button", { name: "Analyze ISO", exact: true }),
  ).toBeEnabled();
  await page.route("**/media/analyze", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      storage_id: 1,
      relative_path: "ubuntu-server-amd64.iso",
    });
    await route.fulfill({ json: { job_id: 43, status: "queued" } });
  });
  await page.getByRole("button", { name: "Analyze ISO", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByRole("status")).toContainText(
    "Analysis job #43 queued",
  );
});
test("HTML upload errors release controls and API outage clears connection status", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Add ISO", exact: true }).click();
  await page
    .getByRole("button", { name: "Upload a file", exact: true })
    .click();
  await page
    .getByLabel("Choose ISO file")
    .setInputFiles({
      name: "test.iso",
      mimeType: "application/octet-stream",
      buffer: Buffer.from("fixture"),
    });
  await page.route("**/media/upload?*", (route) =>
    route.fulfill({
      status: 413,
      contentType: "text/html",
      body: "<h1>Too large</h1>",
    }),
  );
  await page
    .getByRole("button", { name: "Upload & analyze", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("exceeds its size limit");
  await expect(
    page.getByRole("button", { name: "Upload & analyze", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.route("**/api/v1/health", (route) => route.abort());
  await page.getByRole("button", { name: "Refresh data" }).click();
  await expect(
    page.getByText("API unavailable", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(
    "Previously loaded records are shown",
  );
});


test("read-only library disables uploads", async ({page}) => {
  await page.route("**/api/v1/health", route => route.fulfill({json:{status:"ok",storage_read_only:true}}));
  await page.goto("/");
  await expect(page.getByText("API connected",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Add ISO",exact:true}).click();
  await expect(page.getByRole("button",{name:"Upload a file",exact:true})).toBeDisabled();
  await expect(page.getByText("This library is read-only.",{exact:false})).toBeVisible();
});
