CREATE TABLE [dbo].[RoleWorkflows]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [RoleId] bigint NOT NULL,
    [WorkflowInstanceId] bigint NOT NULL
);
