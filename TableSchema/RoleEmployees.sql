CREATE TABLE [dbo].[RoleEmployees]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [RoleId] bigint NOT NULL,
    [EmployeeNumber] nvarchar(20) NOT NULL,
    [Infotype] nvarchar(50) NOT NULL,
    [Subtype] nvarchar(50) NOT NULL,
    [Action] nvarchar(5) NOT NULL
);
