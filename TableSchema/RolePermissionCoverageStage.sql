CREATE TABLE [dbo].[RolePermissionCoverageStage]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [RoleId] bigint NOT NULL,
    [Object] nvarchar(100) NOT NULL,
    [TransactionIdInActivityMode] decimal(18,0) NOT NULL,
    [ActivityModeId] bigint NOT NULL,
    [LastModified] datetime NULL
);
