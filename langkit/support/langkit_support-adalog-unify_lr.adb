with Langkit_Support.Adalog.Debug; use Langkit_Support.Adalog.Debug;

package body Langkit_Support.Adalog.Unify_LR is
   use Left_Var; use Right_Var;

   -----------
   -- Apply --
   -----------

   function Apply (Self : in out Unify_LR) return Solving_State is
      Result : Solving_State;
      L      : L_Type;
      R      : R_Type;
      LC     : R_Type;
   begin
      Trace ("In Unify_LR");

      if Is_Defined (Self.Left) then

         L := Get_Value (Self.Left);
         R := Get_Value (Self.Right);
         LC := Convert (Self.L_Data, L);

         if Is_Defined (Self.Right) then

            --  Both values are defined, return true if they are equal

            Result := +Equals (Self.Eq_Data, LC, R);
            Trace ("In Unify_LR, Left value is : " & Element_Image (L));
            Trace ("In Unify_LR, Right value is : " & Element_Image (R));
            Trace ("In Unify_LR, both defined, returning " & Result'Image);

         elsif Set_Value (Self.Right, LC) then

            --  Left is defined, right is not, give right the value of left and
            --  return true.

            Result := Satisfied;
            Self.State := Right_Changed;
            Trace ("In Unify_LR, propagating right, from "
                   & Image (Self.Left) & " to "
                   & Image (Self.Right));
            Trace ("In Unify_LR, From value is : " & Element_Image (L));
            Trace ("In Unify_LR, Old to value is : " & Element_Image (R));
            Trace ("In Unify_LR, New to value is : " & Element_Image (LC));

         else

            Result := Unsatisfied;
            Trace ("In Unify_LR, propagating right failed! ");
         end if;

         L_Dec_Ref (L);
         R_Dec_Ref (R);
         R_Dec_Ref (LC);
         return Result;
      end if;

      if not Is_Defined (Self.Right) then
         --  TODO??? Another solution, rather than force the users to define
         --  domains for variables before binding them together, would be to
         --  defer unification, like it is done for predicates.
         --
         --  It is not sure it would be better: The outcome would probably
         --  be potentially slower solving. However, it might be that some
         --  equations cannot be expressed easily if we don't have unification
         --  defer.

         raise Early_Binding_Error
           with ("Variables " & Image (Self.Right) & " and "
                 & Image (Self.Left) & " are not defined yet");
      end if;

      --  Right is defined, left is not, give left the value of right and
      --  return true.
      R := Get_Value (Self.Right);
      declare
         RC : L_Type := Convert (Self.R_Data, R);
      begin
         Result := +Set_Value (Self.Left, RC);
         R_Dec_Ref (R);
         L_Dec_Ref (RC);
      end;

      case Result is
         when Progress | No_Progress =>
            raise Program_Error with "not implemented yet";

         when Satisfied =>
            Self.State := Left_Changed;
            Trace ("In Unify_LR, propagating left, from "
                      & Image (Self.Right) & " to "
                      & Image (Self.Left));

         when Unsatisfied =>
            Trace ("In Unify_LR, propagating left failed ! ");
      end case;

      return Result;
   end Apply;

   ------------
   -- Revert --
   ------------

   procedure Revert (Self : in out Unify_LR) is
   begin
      case Self.State is
         when Left_Changed => Reset (Self.Left);
         when Right_Changed => Reset (Self.Right);
         when others => null;
      end case;
      Self.State := No_Change;
   end Revert;
end Langkit_Support.Adalog.Unify_LR;
