CREATE TABLE [dbo].[RolesTransactions]
(
    [RoleId] bigint NOT NULL,
    [TransactionId] decimal(18,0) NOT NULL,
    [AuthorizationId] nvarchar(400) NULL
);
