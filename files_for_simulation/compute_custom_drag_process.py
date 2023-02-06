import KratosMultiphysics

def Factory(settings, Model):
    if(type(settings) != KratosMultiphysics.Parameters):
        raise Exception("expected input shall be a Parameters object, encapsulating a json string")

    return ComputeCustomDragProcess(Model, settings["Parameters"])


class ComputeCustomDragProcess(KratosMultiphysics.Process):
    def __init__(self, Model, settings ):
        KratosMultiphysics.Process.__init__(self)

        default_settings = KratosMultiphysics.Parameters("""
            {
                "model_part_name"           : "please_specify_model_part_name",
                "interval"                  : [0.0, 1e30],
                "reference_point"           : [0.0, 0.0, 0.0],
                "print_drag_to_screen"      : false,
                "write_drag_output_file"    : true
            }
            """)

        # Detect "End" as a tag and replace it by a large number
        if(settings.Has("interval")):
            if(settings["interval"][1].IsString()):
                if(settings["interval"][1].GetString() == "End"):
                    settings["interval"][1].SetDouble(1e30)
                else:
                    raise Exception("The second value of interval can be \"End\" or a number, interval currently:"+settings["interval"].PrettyPrintJsonString())

        settings.ValidateAndAssignDefaults(default_settings)

        self.model_part = Model[settings["model_part_name"].GetString()]
        self.interval = KratosMultiphysics.Vector(2)
        self.interval[0] = settings["interval"][0].GetDouble()
        self.interval[1] = settings["interval"][1].GetDouble()
        self.print_drag_to_screen = settings["print_drag_to_screen"].GetBool()
        self.write_drag_output_file = settings["write_drag_output_file"].GetBool()

        # PMT: added reference point for moment calculation
        self.reference_x = settings["reference_point"][0].GetDouble()
        self.reference_y = settings["reference_point"][1].GetDouble()
        self.reference_z = settings["reference_point"][2].GetDouble()

        if (self.model_part.GetCommunicator().MyPID() == 0):
            if (self.write_drag_output_file):
                # Set drag output file name
                self.drag_filename = settings["model_part_name"].GetString() + "_custom_drag.dat"

                # File creation to store the drag evolution
                with open(self.drag_filename, 'w') as file:
                    file.write(settings["model_part_name"].GetString() + " custom drag \n")
                    file.write("\n")
                    file.write("Time   Fx   Fy   Fz   Mx   My   Mz\n")
                    file.close()


    def ExecuteFinalizeSolutionStep(self):

        current_time = self.model_part.ProcessInfo[KratosMultiphysics.TIME]

        if((current_time >= self.interval[0]) and  (current_time < self.interval[1])):

            # Note that MPI communication is done within VariableUtils().SumHistoricalNodeVectorVariable()
            #reaction_vector = KratosMultiphysics.VariableUtils().SumHistoricalNodeVectorVariable(KratosMultiphysics.REACTION, self.model_part, 0)

            # PMT: TODO: only checked for OpenMP, update for MPI
            fx = 0.0
            fy = 0.0
            fz = 0.0

            mx = 0.0
            my = 0.0
            mz = 0.0       
            
            for node in self.model_part.Nodes:
                reaction = node.GetSolutionStepValue(KratosMultiphysics.REACTION, 0)
                # PMT: NOTE: sign is flipped to go from reaction to action
                fx += (-1) * reaction[0]
                fy += (-1) * reaction[1]
                fz += (-1) * reaction[2]

                x = node.X - self.reference_x
                y = node.Y - self.reference_y
                z = node.Z - self.reference_z
                mx += y * (-1) * reaction[2] - z * (-1) * reaction[1]
                my += z * (-1) * reaction[0] - x * (-1) * reaction[2]
                mz += x * (-1) * reaction[1] - y * (-1) * reaction[0]
                
            if (self.model_part.GetCommunicator().MyPID() == 0):
                if (self.print_drag_to_screen):
                    print("CUSTOM DRAG RESULTS:")
                    print("Current time: " + str(current_time))
                    print("Forces:" + " Fx: " + str(fx) + " Fy: " + str(fy) + " Fz: " + str(fz))
                    print("Moments:" + " Mx: " + str(mx) + " My: " + str(my) + " Mz: " + str(mz))

                if (self.write_drag_output_file):
                    with open(self.drag_filename, 'a') as file:
                        output_str = str(current_time)
                        output_str += "   " + str(fx) + "   " + str(fy) + "   " + str(fz)
                        output_str += "   " + str(mx) + "   " + str(my) + "   " + str(mz) + "\n"
                        file.write(output_str)
                        file.close()
