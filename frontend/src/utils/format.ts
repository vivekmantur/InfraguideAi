export function formatMoney(currency: string, amount: number) {
  return `${currency} ${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function list(items?: string[]) {
  return items?.length ? items.join(", ") : "Not detected";
}
