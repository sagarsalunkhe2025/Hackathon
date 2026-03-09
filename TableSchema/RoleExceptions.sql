CREATE TABLE [dbo].[RoleExceptions]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [ExceptionId] bigint NOT NULL,
    [UserId] bigint NOT NULL,
    [RoleName] nvarchar(400) NOT NULL
);
