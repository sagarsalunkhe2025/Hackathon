CREATE TABLE [dbo].[RoleSplitterRuns]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [Title] nvarchar(150) NOT NULL,
    [OriginalRoleId] bigint NOT NULL,
    [OriginalRoleSystemId] bigint NOT NULL,
    [NewRoleSystemId] bigint NOT NULL,
    [NewRoleName] nvarchar(150) NOT NULL,
    [TransactionsToSplit] nvarchar(MAX) NOT NULL,
    [RunOn] datetime NOT NULL,
    [RunBy] nvarchar(50) NOT NULL,
    [IsAssignUsersToNewRole] bit NOT NULL,
    [IsPerformedAssignUsersToNewRole] bit NOT NULL,
    [IsRemoveUsersFromOriginalRole] bit NOT NULL,
    [IsPerformedRemoveUsersFromOriginalRole] bit NOT NULL,
    [IsCreateNewRole] bit NOT NULL,
    [IsRemoveActivitiesFromOriginalRole] bit NOT NULL,
    [IsReadyForAssigment] bit NULL,
    [IsCompleted] bit NULL,
    [CompletedOn] datetime NULL,
    [WorkflowInstanceId] bigint NULL
);
