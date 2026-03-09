CREATE TABLE [dbo].[RoleHistory]
(
    [UserId] bigint NOT NULL,
    [TimeStamp] datetime NOT NULL,
    [RoleName] nvarchar(400) NOT NULL,
    [LocalTimeStamp] datetime NOT NULL
);
