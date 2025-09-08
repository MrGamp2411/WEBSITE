import { Wallee } from 'wallee';

export const spaceId = Number(process.env.WALLEE_SPACE_ID);
const userId = Number(process.env.WALLEE_USER_ID);
const apiSecret = String(process.env.WALLEE_API_SECRET);

const cfg = { space_id: spaceId, user_id: userId, api_secret: apiSecret };

export const transactionService = new Wallee.api.TransactionService(cfg);
export const paymentPageService = new Wallee.api.TransactionPaymentPageService(cfg);
