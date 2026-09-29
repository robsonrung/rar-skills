// Fixture target: intentionally contains both unnecessary code and useful seams.

export function hasValue(value) {
  // Return whether the value is present.
  return value !== null && value !== undefined && value !== "";
}

export async function loadOne(load) {
  // The public consumer expects an array, including for one result.
  return Promise.all([load()]);
}

export function withResource(resource, work) {
  try {
    return work(resource);
  } finally {
    resource.release();
  }
}

export function readLimit(payload) {
  // Payloads arrive from JSON; static annotations cannot validate them.
  if (payload === null || typeof payload !== "object" ||
      typeof payload.limit !== "number" || !Number.isInteger(payload.limit) || payload.limit < 0) {
    throw new TypeError("limit must be a non-negative integer");
  }
  return payload.limit;
}

export function tenantAmounts(rows, tenantId) {
  return rows.filter(row => row.tenantId === tenantId)
    .map(row => ({ id: row.id, amount: row.amount ?? 0 }));
}

export function sumPositive(values) {
  // Initialize the total to zero.
  let total = 0;
  for (const value of values) {
    if (value > 0) {
      const next = total + value;
      total = next;
    }
  }
  return total;
}

// Purchasing and sales own independent policies; equal current rates are coincidental.
export function purchaseFee(amount) {
  return amount * 0.02;
}

export function salesCommission(amount) {
  return amount * 0.02;
}

function unusedDebugFormatter(value) {
  return `debug: ${value}`;
}
